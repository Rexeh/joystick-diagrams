"""Modifier presentation: the ``style`` hook that writes rich modifier text (plan §2.2C/G/H).

After the fill stage every slot holds plain text. This hook asks the resolver
for the *rich* version of each single-token slot (``BindingResolver.rich_for``)
and, when it differs from plain text, rewrites the slot's three surfaces:

- the innermost foreignObject ``<div>`` (or the deepest single wrapper inside it,
  so ``<font style="font-size: 9px">`` in the VKB templates keeps its size):
  one ``<div>`` per line (carrying the line's relative size, as draw.io's own
  multi-line labels do), coloured runs as ``<span style="color: …">``;
- the ``<text>`` fallback: one ``<tspan x dy>`` per line, coloured runs as
  nested ``<tspan fill>``;
- the draw.io model label: ``html=1`` with escaped ``<br>``/``<font color>``
  markup, so the export reopens in draw.io looking the same.

Modifier boxes (``*_MODIFIER_N``, ``_KEY``, ``_ACTION``) also take the stroke
colour of their binding's highest-priority key when "Colour by modifier key" is
on. Key text is always printed, so colour never carries meaning alone.

Text fit (spike S5, ``render/text_fit.py``)
-------------------------------------------
Before a rich label is written it is fitted to its box: the font the template
or theme decided (read back from the innermost div, after the theme writer ran)
is shrunk down to the role's ``min_font_size`` until the wrapped block fits the
box, and when even that is not enough the trailing modifier lines are replaced
by ``+N more``. The chosen size is written to all three surfaces (the host
div's ``font-size``, the ``<text>`` attribute, the cell's ``fontSize``) so the
SVG, Inkscape and draw.io agree; dropped lines are reported through
``RenderReport.overflow`` and ``details``. Only slots that receive rich text
are fitted, so plain labels keep the template's own layout.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

from lxml import etree

from joystick_diagrams.render.adapters._common import (
    SVG,
    XHTML,
    localname,
    offset_rect,
    rect_of,
)
from joystick_diagrams.render.binding import Line, RichText, Run
from joystick_diagrams.render.drawio_model import MxCell
from joystick_diagrams.render.slots import (
    Capability,
    Rect,
    Slot,
    SlotRole,
    TextTarget,
    TextTargetKind,
)
from joystick_diagrams.render.style_writer import (
    format_declarations,
    parse_declarations,
    style_cell_box,
    style_shape,
    theme_role_for,
)
from joystick_diagrams.render.text_fit import (
    DEFAULT_FONT_SIZE,
    DEFAULT_MIN_FONT_SIZE,
    FitBox,
    FitResult,
    FontSpec,
    fit_rich,
    line_em,
)
from joystick_diagrams.render.theme import BoxStyle, TextStyle

if TYPE_CHECKING:
    from joystick_diagrams.render.pipeline import RenderJob

BOX_SLOT_ROLES = frozenset(
    {SlotRole.MODIFIER, SlotRole.MODIFIER_KEY, SlotRole.MODIFIER_ACTION}
)
_WRAPPER_TAGS = frozenset({"font", "span", "b", "i", "strong", "em", "div"})
LINE_HEIGHT_EM = 1.2
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


def _clear(element: Any) -> None:
    element.text = None
    for child in list(element):
        element.remove(child)


def _append_text(host: Any, text: str) -> None:
    children = list(host)
    if children:
        children[-1].tail = (children[-1].tail or "") + text
    else:
        host.text = (host.text or "") + text


def _run_declarations(run: Run) -> dict[str, str]:
    declarations: dict[str, str] = {}
    if run.colour is not None:
        declarations["color"] = run.colour
    if run.bold:
        declarations["font-weight"] = "bold"
    if run.size_em is not None:
        declarations["font-size"] = f"{run.size_em:g}em"
    return declarations


def _append_html_run(host: Any, run: Run) -> None:
    declarations = _run_declarations(run)
    if not declarations:
        _append_text(host, run.text)
        return
    span = etree.SubElement(host, f"{XHTML}span")
    span.set("style", format_declarations(declarations).strip())
    span.text = run.text


def _line_runs(line: Line, em: float) -> Line:
    """The runs of a line whose shared size ``em`` moved onto the line's block."""
    if em == 1.0 and all(run.size_em is None for run in line):
        return line
    return tuple(Run(run.text, run.colour, run.bold, None) for run in line)


def _append_html_line(host: Any, line: Line) -> None:
    block = etree.SubElement(host, f"{XHTML}div")
    em = line_em(line)
    if em != 1.0:
        block.set("style", f"font-size: {em:g}em;")
    for run in _line_runs(line, em):
        _append_html_run(block, run)


def write_foreign_object(
    div: Any, rich: RichText, fit: FitResult | None = None
) -> None:
    """One block per line; a single line is written inline, as the template had it."""
    host = content_host(div)
    _clear(host)
    if len(rich.lines) == 1:
        for run in rich.lines[0]:
            _append_html_run(host, run)
    else:
        for line in rich.lines:
            _append_html_line(host, line)
    if fit is not None:
        apply_fit_to_div(div, fit)


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


def apply_fit_to_div(div: Any, fit: FitResult) -> None:
    """Put the fitted size (and leading) on the block so the CSS strut follows.

    Wrappers between the block and the text (``<font style="font-size: 9px">``)
    lose their own size: the block's line boxes are ``line-height × block
    size`` tall whatever the inline size, so the size must live on the block.
    """
    declarations = parse_declarations(div.get("style"))
    block_size = css_px(declarations.get("font-size"))
    if fit.shrunk or block_size != fit.font_size:
        declarations["font-size"] = _font_size_px(fit.font_size)
        for element in _lineage(div):
            if element is not div:
                _strip_font_size(element)
    if fit.compact:
        declarations["line-height"] = f"{fit.line_height:g}"
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
    return width or None


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


# ── <text> fallback ──


def _append_svg_run(parent: Any, run: Run) -> None:
    if run.is_plain:
        _append_text(parent, run.text)
        return
    tspan = etree.SubElement(parent, f"{SVG}tspan")
    if run.colour is not None:
        tspan.set("fill", run.colour)
    if run.bold:
        tspan.set("font-weight", "bold")
    if run.size_em is not None:
        tspan.set("font-size", f"{run.size_em:g}em")
    tspan.text = run.text


def _line_tspan(
    text_element: Any,
    index: int,
    ems: list[float],
    line_height: float = LINE_HEIGHT_EM,
) -> Any:
    """A line's ``<tspan x dy font-size>``; ``dy`` is in the tspan's own em."""
    tspan = etree.SubElement(text_element, f"{SVG}tspan")
    x = text_element.get("x")
    if x is not None:
        tspan.set("x", x)
    em = ems[index]
    if em != 1.0:
        tspan.set("font-size", f"{em:g}em")
    if index == 0:
        # Keep the block vertically centred on the original baseline.
        following = sum(ems[1:]) * line_height
        tspan.set("dy", f"{-following / 2 / em:g}em")
    else:
        tspan.set("dy", f"{line_height:g}em")
    return tspan


def write_text_element(
    text_element: Any, rich: RichText, fit: FitResult | None = None
) -> None:
    """Write ``rich`` as tspans; with a ``fit``, its word-wrapped lines and size."""
    _clear(text_element)
    lines = fit.wrapped if fit is not None else rich.lines
    line_height = fit.line_height if fit is not None else LINE_HEIGHT_EM
    if fit is not None and fit.shrunk:
        text_element.set("font-size", _font_size_px(fit.font_size))
    if len(lines) == 1:
        for run in lines[0]:
            _append_svg_run(text_element, run)
        return
    ems = [line_em(line) for line in lines]
    for index, line in enumerate(lines):
        tspan = _line_tspan(text_element, index, ems, line_height)
        for run in _line_runs(line, ems[index]):
            _append_svg_run(tspan, run)


def write_text_target(
    target: TextTarget, rich: RichText, fit: FitResult | None = None
) -> None:
    if target.kind is TextTargetKind.FOREIGN_OBJECT:
        write_foreign_object(target.element, rich, fit)
    else:
        write_text_element(target.element, rich, fit)


# ── draw.io model label ──


def _html_run(run: Run) -> str:
    text = html.escape(run.text, quote=False)
    if run.bold:
        text = f"<b>{text}</b>"
    if run.size_em is not None:
        text = f'<span style="font-size: {run.size_em:g}em">{text}</span>'
    if run.colour is not None:
        text = f'<font color="{run.colour}">{text}</font>'
    return text


def _html_line(line: Line) -> str:
    return "".join(_html_run(run) for run in line)


def rich_html(rich: RichText) -> str:
    """The ``html=1`` label markup for a draw.io cell."""
    return "<br>".join(_html_line(line) for line in rich.lines)


def write_cell_label(
    cell: MxCell, rich: RichText, fit: FitResult | None = None
) -> None:
    style = cell.style_dict
    changed = False
    if style.get("html") != "1":
        style["html"] = "1"
        changed = True
    if fit is not None and style.get("fontSize") != f"{fit.font_size:g}":
        style["fontSize"] = f"{fit.font_size:g}"
        changed = True
    if changed:
        cell.set_style_dict(style)
    label = rich_html(rich)
    if fit is not None and fit.compact:
        label = f'<div style="line-height: {fit.line_height:g}">{label}</div>'
    cell.set_label(label)


# ── Hook ──


def _overflow_for(job: RenderJob, slot: Slot) -> int:
    if slot.input_key is None or slot.role is not SlotRole.ACTION:
        return 0
    return job.overflow.get(slot.input_key.upper(), 0)


def _text_style_for(job: RenderJob, slot: Slot) -> TextStyle | None:
    theme = job.ctx.theme
    role = theme_role_for(slot, bound=True)
    return theme.text(role) if theme is not None and role is not None else None


def _first_target(slot: Slot, kind: TextTargetKind) -> Any | None:
    return next((t.element for t in slot.text_targets if t.kind is kind), None)


def fit_for_slot(
    job: RenderJob, slot: Slot, rich: RichText, frames: list[Rect] | None = None
) -> FitResult | None:
    """Shrink/truncate ``rich`` for ``slot``; ``None`` when nothing is known to fit to.

    ``frames`` is ``painted_frames(job.doc.root)``, computed once per render by
    the caller; ``None`` computes it here.
    """
    assert job.slots is not None
    style = _text_style_for(job, slot)
    if style is not None and style.fit == "none":
        return None
    div = _first_target(slot, TextTargetKind.FOREIGN_OBJECT)
    text_element = _first_target(slot, TextTargetKind.TEXT)
    if div is not None:
        font = foreign_font(div)
    elif text_element is not None:
        font = text_element_font(text_element)
    else:
        return None
    if frames is None:
        frames = painted_frames(job.doc.root) if job.doc is not None else []
    box = slot_fit_box(slot, div, frames, job.slots.offset)
    if box.width is None and box.height is None:
        return None
    min_size = (
        style.min_font_size
        if style is not None and style.min_font_size
        else DEFAULT_MIN_FONT_SIZE
    )
    protected = 1 if slot.role is SlotRole.ACTION else 0
    return fit_rich(rich, box, font, min_size=min_size, protected=protected)


def _record_truncation(job: RenderJob, slot: Slot, fit: FitResult) -> None:
    if not fit.truncated and fit.fits:
        return
    if fit.truncated and slot.input_key is not None:
        key = slot.input_key.upper()
        job.overflow[key] = max(job.overflow.get(key, 0), fit.truncated)
    if fit.truncated:
        job.details.append(
            f"{slot.key.upper()}: {fit.truncated} modifier line(s) hidden "
            f"(box too small at {fit.font_size:g}px)"
        )
    else:
        job.details.append(
            f"{slot.key.upper()}: text overflows its box at {fit.font_size:g}px"
        )


def _write_rich(job: RenderJob, slot: Slot, rich: RichText, frames: list[Rect]) -> None:
    assert job.slots is not None
    fit = fit_for_slot(job, slot, rich, frames)
    if fit is not None:
        _record_truncation(job, slot, fit)
        rich = RichText(fit.lines)
    if Capability.TEXT_STYLE in job.slots.capabilities or Capability.TEXT in (
        job.slots.capabilities
    ):
        for target in slot.text_targets:
            write_text_target(target, rich, fit)
    if slot.cell is not None:
        write_cell_label(slot.cell, rich, fit)


def _colour_modifier_box(job: RenderJob, slot: Slot) -> None:
    assert job.slots is not None
    if not job.ctx.colour_modifiers or slot.role not in BOX_SLOT_ROLES:
        return
    if slot.input_key is None or slot.modifier_index is None:
        return
    modifier = job.resolver.modifier_for(slot.input_key, slot.modifier_index)
    colour = job.resolver.modifier_box_colour(modifier) if modifier else None
    if colour is None:
        return
    box = BoxStyle(stroke=colour)
    if Capability.SHAPE_STYLE in job.slots.capabilities and slot.shape is not None:
        style_shape(slot.shape, box)
    if slot.cell is not None:
        style_cell_box(slot.cell, box)


def apply_modifier_presentation(job: RenderJob) -> None:
    """Style hook: rich modifier text and modifier-box colours for single-token slots."""
    if job.slots is None:
        return
    frames: list[Rect] | None = None  # painted shapes, scanned on first use
    for slot in job.slots.slots:
        if len(slot.tokens) != 1:
            continue  # multi-token labels keep the plain fill
        rich = job.resolver.rich_for(slot.key, _overflow_for(job, slot))
        if rich is not None and not rich.is_plain:
            if frames is None:
                frames = painted_frames(job.doc.root) if job.doc is not None else []
            _write_rich(job, slot, rich, frames)
        _colour_modifier_box(job, slot)
    job.write_model()


__all__ = [
    "apply_fit_to_div",
    "apply_modifier_presentation",
    "content_host",
    "css_px",
    "fit_for_slot",
    "foreign_box_width",
    "foreign_font",
    "label_centre",
    "painted_frames",
    "rich_html",
    "slot_fit_box",
    "visible_frame",
    "write_cell_label",
    "write_foreign_object",
    "write_text_element",
]

if __name__ == "__main__":
    pass
