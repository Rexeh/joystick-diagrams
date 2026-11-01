"""Text fit for one slot: what box, what font, which size (plan §1.2, spike S5).

The decision side of fitting, shared by the two writers in
``render/modifier_presentation.py`` (rich labels with modifier lines, and plain
labels under "Auto"). Everything is read back from the document *after* the
theme writer ran, so a theme's own size is what the fit starts from.

- **Font**: ``foreign_font`` (nearest declared size, family, bold anywhere in
  the wrapper chain) or ``text_element_font`` for ``<text>``-only labels.
- **Box**: ``slot_fit_box``: width from draw.io's flex div (else the cell less
  its spacing), height from the cell geometry, clamped to the smallest painted
  frame around an invisible text cell (``visible_frame``).
- **Policy** (``fit_policy``): the role's ``TextStyle.fit``:
  ``"shrink"``/``None`` fits labels that get modifier lines, from the
  template/theme size down to ``min_font_size``; ``"auto"`` fits *every*
  label and takes the largest size that fits, from ``min_font_size`` up to the
  ceiling (``auto_ceiling``); ``"none"`` fits nothing. Under "Auto" the box is
  narrowed by ``AUTO_PADDING_PX`` per side so grown text keeps clear of the
  stroke.
- **Plain text** (``plain_lines``): the visible lines of a label as written by
  the fill (``<br>`` and block children break lines), never truncated.

Original (unchanged) never reaches this module: the legacy engine renders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from joystick_diagrams.render.adapters._common import localname, offset_rect, rect_of
from joystick_diagrams.render.binding import RichText, Run
from joystick_diagrams.render.slots import Rect, Slot, SlotRole, TextTargetKind
from joystick_diagrams.render.style_writer import (
    format_declarations,
    parse_declarations,
    strip_conflicting_markup,
    theme_role_for,
)
from joystick_diagrams.render.text_fit import (
    DEFAULT_FONT_SIZE,
    DEFAULT_MIN_FONT_SIZE,
    FitBox,
    FitResult,
    FontSpec,
    fit_rich,
)
from joystick_diagrams.render.theme import TextStyle

if TYPE_CHECKING:
    from joystick_diagrams.render.pipeline import RenderJob

_WRAPPER_TAGS = frozenset({"font", "span", "b", "i", "strong", "em", "div"})
_BLOCK_TAGS = frozenset({"div", "p", "li"})
LABEL_SPACING_PX = 2.0  # draw.io's default label spacing inside a box
_HTML_FONT_SIZES = {
    "1": 10.0,
    "2": 13.0,
    "3": 16.0,
    "4": 18.0,
    "5": 24.0,
    "6": 32.0,
    "7": 48.0,
}
_BOLD_WEIGHTS = frozenset({"bold", "bolder", "600", "700", "800", "900"})
_BOLD_TAGS = frozenset({"b", "strong"})
_FRAME_TAGS = frozenset({"rect", "ellipse", "circle", "path", "polygon"})
FRAME_AREA_RATIO = 4.0  # a frame may be at most this many times the label's area
DEFAULT_MAX_FONT_SIZE = 18.0  # "auto" growth cap when the style sets none
AUTO_GROWTH_FACTOR = 2.0  # "auto" grows to at most this times the template size
AUTO_PADDING_PX = 1.0  # "auto" keeps this much clear inside the box, left and right
_SPACE_RE = re.compile(r"\s+")


def css_px(value: str | None) -> float | None:
    """``"8px"`` / ``"6pt"`` / ``"9"`` → px; ``None`` for anything else."""
    if value is None:
        return None
    text = value.strip().lower()
    try:
        if text.endswith("px"):
            return float(text[:-2])
        if text.endswith("pt"):
            return float(text[:-2]) * 4 / 3
        return float(text)
    except ValueError:
        return None


def _font_size_px(value: float | None) -> str:
    return f"{value:g}px"


# ── foreignObject ──


def content_host(div: Any) -> Any:
    """The deepest element that alone wraps the text (keeps ``<font size>`` wrappers)."""
    host = div
    while True:
        children = [child for child in host if isinstance(child.tag, str)]
        if (
            len(children) != 1
            or (host.text or "").strip()
            or (children[0].tail or "").strip()
            or localname(children[0]) not in _WRAPPER_TAGS
        ):
            return host
        host = children[0]


def _strip_font_size(element: Any) -> None:
    declarations = parse_declarations(element.get("style"))
    if "font-size" in declarations:
        del declarations["font-size"]
        if declarations:
            element.set("style", format_declarations(declarations))
        else:
            del element.attrib["style"]
    if localname(element) == "font" and element.get("size") is not None:
        del element.attrib["size"]


def apply_fit_to_div(
    div: Any, fit: FitResult, *, every_descendant: bool = False
) -> None:
    """Put the fitted size (and leading) on the block so the CSS strut follows.

    Wrappers between the block and the text (``<font style="font-size: 9px">``)
    lose their own size: the block's line boxes are ``line-height × block
    size`` tall whatever the inline size, so the size must live on the block.
    ``every_descendant`` also clears sizes deeper in the label (a plain label
    keeps the template's own markup, which may size each line). A label that
    draw.io set ``nowrap`` wraps once the fit broke it into more lines.
    """
    declarations = parse_declarations(div.get("style"))
    block_size = css_px(declarations.get("font-size"))
    if fit.shrunk or block_size != fit.font_size:
        declarations["font-size"] = _font_size_px(fit.font_size)
        for element in _lineage(div):
            if element is not div:
                _strip_font_size(element)
    if every_descendant:
        strip_conflicting_markup(div, {"font-size"})
    line_height = declarations.get("line-height")
    if fit.compact or (
        line_height is not None and css_px(line_height) != fit.line_height
    ):
        declarations["line-height"] = f"{fit.line_height:g}"
    if declarations.get("white-space") == "nowrap" and len(fit.wrapped) > len(
        fit.lines
    ):
        declarations["white-space"] = "normal"
    div.set("style", format_declarations(declarations))


# ── Fonts and boxes read back from the document ──


def _lineage(div: Any) -> list[Any]:
    """``content_host(div)`` up to and including ``div``."""
    host = content_host(div)
    chain = [host]
    while host is not div and host.getparent() is not None:
        host = host.getparent()
        chain.append(host)
    return chain


def foreign_font(div: Any) -> FontSpec:
    """The font the label's text is set in: nearest declaration wins, bold anywhere."""
    size: float | None = None
    family: str | None = None
    bold = False
    for element in _lineage(div):
        declarations = parse_declarations(element.get("style"))
        is_font = localname(element) == "font"
        if size is None:
            size = css_px(declarations.get("font-size"))
            if size is None and is_font:
                size = _HTML_FONT_SIZES.get((element.get("size") or "").strip())
        if family is None:
            family = declarations.get("font-family") or (
                element.get("face") if is_font else None
            )
        if declarations.get("font-weight", "").lower() in _BOLD_WEIGHTS or (
            localname(element) in _BOLD_TAGS
        ):
            bold = True
    return FontSpec(family or "Helvetica", size or DEFAULT_FONT_SIZE, bold)


def text_element_font(text_element: Any) -> FontSpec:
    size = css_px(text_element.get("font-size"))
    weight = (text_element.get("font-weight") or "").lower()
    return FontSpec(
        text_element.get("font-family") or "Helvetica",
        size or DEFAULT_FONT_SIZE,
        weight in _BOLD_WEIGHTS,
    )


def _flex_declarations(div: Any) -> dict[str, str] | None:
    """The style of draw.io's outer flex div (``width``/``margin-left``/``padding-top``)."""
    for ancestor in div.iterancestors():
        declarations = parse_declarations(ancestor.get("style"))
        if "width" in declarations:
            return declarations
        if localname(ancestor) == "foreignObject":
            break
    return None


def foreign_box_width(div: Any) -> float | None:
    """The wrapping width draw.io gave the label (the flex div's ``width``)."""
    declarations = _flex_declarations(div)
    width = css_px(declarations.get("width")) if declarations else None
    # ``nowrap`` labels get a 1 px flex div: the cell decides their width.
    return width if width is not None and width > 1 else None


def label_centre(div: Any) -> tuple[float, float] | None:
    """Where draw.io centred the label, in rendered coordinates."""
    declarations = _flex_declarations(div)
    if not declarations:
        return None
    left = css_px(declarations.get("margin-left"))
    width = css_px(declarations.get("width"))
    top = css_px(declarations.get("padding-top"))
    if left is None or width is None or top is None:
        return None
    return left + width / 2, top


def _paints(element: Any, attribute: str) -> bool:
    value = element.get(attribute)
    return value is not None and value.strip().lower() != "none"


def painted_frames(root: Any) -> list[Rect]:
    """Bounding boxes of every shape that draws something (rendered coordinates)."""
    frames: list[Rect] = []
    for element in root.iter():
        if localname(element) not in _FRAME_TAGS:
            continue
        if not (_paints(element, "stroke") or _paints(element, "fill")):
            continue
        rect = rect_of(element)
        if rect is not None and rect.width > 0 and rect.height > 0:
            frames.append(rect)
    return frames


def visible_frame(rect: Rect, frames: list[Rect]) -> Rect | None:
    """The smallest painted shape around a label (centre inside, area capped).

    Some templates put an invisible text cell over a separately drawn frame;
    the frame is what the reader sees, so it bounds the text. (A frame that is
    part of a background image is invisible to this lookup.)
    """
    cx, cy = rect.x + rect.width / 2, rect.y + rect.height / 2
    best: Rect | None = None
    for frame in frames:
        inside = (
            frame.x <= cx <= frame.x + frame.width
            and frame.y <= cy <= frame.y + frame.height
        )
        if not inside or frame.area > FRAME_AREA_RATIO * rect.area:
            continue
        if best is None or frame.area < best.area:
            best = frame
    return best


def _own_shape_paints(slot: Slot) -> bool:
    shape = slot.shape.element if slot.shape is not None else None
    if shape is None:
        return False
    return any(
        _paints(el, "stroke") or _paints(el, "fill")
        for el in shape.iter()
        if localname(el) in _FRAME_TAGS or localname(el) == "image"
    )


def _rendered_rect(slot: Slot, offset, div: Any | None) -> Rect | None:
    """The label's box in rendered coordinates: its shape, else its cell geometry
    placed where the foreignObject centres the label, else geometry + offset."""
    if slot.bbox is not None:
        return slot.bbox
    geometry = slot.cell.geometry if slot.cell is not None else None
    if geometry is None:
        return None
    centre = label_centre(div) if div is not None else None
    if centre is not None:
        return Rect(
            centre[0] - geometry.width / 2,
            centre[1] - geometry.height / 2,
            geometry.width,
            geometry.height,
        )
    return offset_rect(geometry, offset)


def _slot_rect(
    slot: Slot, frames: list[Rect] = (), offset=None, div: Any | None = None
) -> Rect | None:
    """The label's box: its cell geometry, clamped to a visible frame around it."""
    rect = None
    if slot.cell is not None and slot.cell.geometry is not None:
        rect = slot.cell.geometry
    elif slot.bbox is not None:
        rect = slot.bbox
    elif slot.shape is not None:
        rect = slot.shape.bbox
    if rect is None or not frames or _own_shape_paints(slot):
        return rect
    rendered = _rendered_rect(slot, offset, div)
    frame = visible_frame(rendered, frames) if rendered is not None else None
    if frame is None:
        return rect
    return Rect(
        rect.x, rect.y, min(rect.width, frame.width), min(rect.height, frame.height)
    )


def slot_fit_box(
    slot: Slot, div: Any | None, frames: list[Rect] = (), offset=None
) -> FitBox:
    """Width from the foreignObject (else the box less spacing), height from the box.

    The text block is centred vertically, so the whole box height is usable;
    rotated labels keep only the width (their box is in rotated coordinates).
    ``frames`` (``painted_frames``) lets an invisible text cell take the size of
    the visible frame drawn around it.
    """
    width = foreign_box_width(div) if div is not None else None
    rect = _slot_rect(slot, frames, offset, div)
    height = None
    if rect is not None:
        inner = max(rect.width - LABEL_SPACING_PX, 0) or None
        width = inner if width is None or (inner and inner < width) else width
        if not slot.rotated:
            height = rect.height or None
    return FitBox(width, height)


# ── Policy and the fit ──


def text_style_for(job: RenderJob, slot: Slot, bound: bool = True) -> TextStyle | None:
    """The theme's text style for ``slot``; ``None`` under Original (unchanged)."""
    theme = job.ctx.theme
    role = theme_role_for(slot, bound=bound)
    return theme.text(role) if theme is not None and role is not None else None


def _first_target(slot: Slot, kind: TextTargetKind) -> Any | None:
    return next((t.element for t in slot.text_targets if t.kind is kind), None)


@dataclass(frozen=True)
class FitPolicy:
    mode: str  # "shrink" | "auto"
    min_size: float
    size: float | None  # the role's explicit size (the "auto" ceiling when set)
    max_size: float  # the "auto" growth cap


def fit_policy(style: TextStyle | None) -> FitPolicy | None:
    """How a role fits its text; ``None`` when it opted out (``fit="none"``)."""
    mode = (style.fit if style is not None else None) or "shrink"
    if mode == "none":
        return None
    min_size = (
        style.min_font_size
        if style is not None and style.min_font_size
        else DEFAULT_MIN_FONT_SIZE
    )
    max_size = (
        style.max_font_size
        if style is not None and style.max_font_size
        else DEFAULT_MAX_FONT_SIZE
    )
    size = style.font_size if style is not None else None
    return FitPolicy(mode, min_size, size, max_size)


def auto_ceiling(policy: FitPolicy, template_size: float) -> float:
    """The largest size "Auto" may use: the role's own size when set, else up to
    twice the template's size, capped at ``max_size`` but never below the
    template's own size."""
    if policy.size:
        return policy.size
    grown = min(AUTO_GROWTH_FACTOR * template_size, policy.max_size)
    return max(template_size, grown)


def slot_is_bound(job: RenderJob, slot: Slot) -> bool:
    """Whether any token of the slot shows a binding (the theme writer's role test)."""
    return any(job.resolver.text_for(token) for token in slot.tokens)


def is_auto(job: RenderJob, slot: Slot) -> bool:
    """Whether the slot's role fits every label ("Auto")."""
    policy = fit_policy(text_style_for(job, slot, slot_is_bound(job, slot)))
    return job.ctx.theme is not None and policy is not None and policy.mode == "auto"


def slot_font(slot: Slot) -> tuple[FontSpec, Any | None] | None:
    """The label's font and its foreignObject block (``None`` without a target)."""
    div = _first_target(slot, TextTargetKind.FOREIGN_OBJECT)
    if div is not None:
        return foreign_font(div), div
    text_element = _first_target(slot, TextTargetKind.TEXT)
    if text_element is not None:
        return text_element_font(text_element), None
    return None


def fit_for_slot(
    job: RenderJob,
    slot: Slot,
    rich: RichText,
    frames: list[Rect] | None = None,
    *,
    plain: bool = False,
) -> FitResult | None:
    """Fit ``rich`` to ``slot``'s box; ``None`` when nothing is known to fit to.

    ``frames`` is ``painted_frames(job.doc.root)``, computed once per render by
    the caller; ``None`` computes it here. ``plain`` text (no modifier lines)
    is only fitted under "Auto" and never loses a line.
    """
    assert job.slots is not None
    bound = slot_is_bound(job, slot) if plain else True
    policy = fit_policy(text_style_for(job, slot, bound))
    if policy is None or (plain and policy.mode != "auto"):
        return None
    found = slot_font(slot)
    if found is None:
        return None
    font, div = found
    if frames is None:
        frames = painted_frames(job.doc.root) if job.doc is not None else []
    box = slot_fit_box(slot, div, frames, job.slots.offset)
    if box.width is None and box.height is None:
        return None
    max_size = None
    if policy.mode == "auto":
        box = box.inset(AUTO_PADDING_PX)
        if box.width is not None and box.height is not None:
            max_size = auto_ceiling(policy, font.size)
    if plain:
        protected = len(rich.lines)
    else:
        protected = 1 if slot.role is SlotRole.ACTION else 0
    return fit_rich(
        rich,
        box,
        font,
        min_size=policy.min_size,
        protected=protected,
        max_size=max_size,
    )


# ── Plain text read back from the document ──


def _collect_lines(element: Any, out: list[list[str]]) -> None:
    """Append ``element``'s visible text to ``out``, starting a line at breaks."""
    name = localname(element) if isinstance(element.tag, str) else ""
    block = name in _BLOCK_TAGS
    if block and out[-1]:
        out.append([])
    if element.text:
        out[-1].append(element.text)
    for child in element:
        if not isinstance(child.tag, str):
            if child.tail:
                out[-1].append(child.tail)
            continue
        if localname(child) == "br":
            out.append([])
        else:
            _collect_lines(child, out)
        if child.tail:
            out[-1].append(child.tail)
    if block and out[-1]:
        out.append([])


def plain_lines(element: Any) -> tuple[tuple[Run, ...], ...]:
    """The label's visible lines (whitespace collapsed as CSS does), one run each."""
    out: list[list[str]] = [[]]
    if localname(element) == "text":
        out[-1].append("".join(element.itertext()))
    else:
        _collect_lines(element, out)
    lines = []
    for parts in out:
        text = _SPACE_RE.sub(" ", "".join(parts)).strip()
        if text:
            lines.append((Run(text),))
    return tuple(lines)


def slot_plain_text(slot: Slot) -> RichText | None:
    """The plain text a slot shows after the fill, ``None`` when it is empty."""
    target = _first_target(slot, TextTargetKind.FOREIGN_OBJECT)
    if target is None:
        target = _first_target(slot, TextTargetKind.TEXT)
    if target is None:
        return None
    lines = plain_lines(target)
    return RichText(lines) if lines else None


__all__ = [
    "AUTO_PADDING_PX",
    "DEFAULT_MAX_FONT_SIZE",
    "FitPolicy",
    "apply_fit_to_div",
    "auto_ceiling",
    "content_host",
    "css_px",
    "fit_for_slot",
    "fit_policy",
    "foreign_box_width",
    "foreign_font",
    "is_auto",
    "label_centre",
    "painted_frames",
    "plain_lines",
    "slot_is_bound",
    "slot_fit_box",
    "slot_font",
    "slot_plain_text",
    "text_element_font",
    "text_style_for",
    "visible_frame",
]

if __name__ == "__main__":
    pass
