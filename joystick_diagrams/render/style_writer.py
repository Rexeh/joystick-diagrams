"""Theme writer: the ``style`` pipeline hook that applies a ``Theme`` (plan §3.6).

Where styles are written, per slot and only within the adapter's capabilities:

- **foreignObject HTML** (``TEXT_STYLE``): the innermost ``<div>`` gets
  ``font-family``/``font-size``/``font-weight``/``font-style``/``color``; the
  same properties are stripped from descendant inline styles and ``<font>``
  attributes (seventeen bundled templates nest ``<font style="font-size: 9px">``
  inside the div), and ``<b>``/``<i>`` wrappers are unwrapped when the theme
  decides weight/style. ``data-drawio-colors`` on the middle div follows.
- **``<text>`` fallback** (``TEXT_STYLE``): ``fill`` and ``font-*`` attributes.
- **Cell shapes** (``SHAPE_STYLE``): ``fill``/``stroke``/``stroke-width`` and, on
  ``<rect>``, ``rx``/``ry``. Themes *recolour*; they never invent a box: a
  stroke is only written where the template draws one, a fill only where one
  exists, and label backings with neither are left alone.
- **Attached edges** (``EDGES``): the stroke path gets colour and width, the
  arrowhead paths get the colour as fill and stroke.
- **draw.io model** (when the slot's cell is known): ``fontColor``,
  ``fontFamily``, ``fontSize``, ``fontStyle`` (bits 1/2 only; 4 underline and 8
  strikethrough are preserved), ``strokeColor``, ``fillColor``, ``strokeWidth``,
  ``rounded``/``absoluteArcSize``/``arcSize`` so the export reopens styled.

Everything is written through small per-element functions so the module stays
under the repo's complexity limits without suppressions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from joystick_diagrams.render.adapters._common import SHAPE_TAGS, localname
from joystick_diagrams.render.drawio_model import MxCell
from joystick_diagrams.render.slots import (
    Capability,
    EdgeRef,
    ShapeRef,
    Slot,
    SlotRole,
    TextTarget,
    TextTargetKind,
)
from joystick_diagrams.render.theme import (
    BoxStyle,
    LineStyle,
    TextStyle,
    Theme,
    ThemeRole,
    font_stack,
)

if TYPE_CHECKING:
    from joystick_diagrams.render.pipeline import RenderJob

MODIFIER_SLOT_ROLES = frozenset(
    {
        SlotRole.MODIFIER,
        SlotRole.MODIFIER_KEY,
        SlotRole.MODIFIER_ACTION,
        SlotRole.MODIFIERS,
    }
)
_FONT_ATTR_FOR_PROPERTY = {"color": "color", "font-size": "size", "font-family": "face"}
_UNWRAP_FOR_PROPERTY = {
    "font-weight": frozenset({"b", "strong"}),
    "font-style": frozenset({"i", "em"}),
}
FONT_STYLE_BOLD = 1
FONT_STYLE_ITALIC = 2


# ── CSS declarations ──


def parse_declarations(style: str | None) -> dict[str, str]:
    """``"a: b; c:d"`` → ``{"a": "b", "c": "d"}`` (ordered, names lower-cased)."""
    result: dict[str, str] = {}
    for part in (style or "").split(";"):
        name, sep, value = part.partition(":")
        if sep and name.strip():
            result[name.strip().lower()] = value.strip()
    return result


def format_declarations(declarations: dict[str, str]) -> str:
    """Inverse of ``parse_declarations`` in draw.io's ``name: value; `` spacing."""
    return "".join(f"{name}: {value}; " for name, value in declarations.items())


def _set_style(element: Any, declarations: dict[str, str]) -> None:
    if declarations:
        element.set("style", format_declarations(declarations))
    elif element.get("style") is not None:
        del element.attrib["style"]


def _number(value: float) -> str:
    return f"{value:g}"


def css_text_properties(text: TextStyle) -> dict[str, str]:
    """The CSS declarations a ``TextStyle`` decides (unset fields are absent)."""
    props: dict[str, str] = {}
    if text.font_family is not None:
        props["font-family"] = font_stack(text.font_family)
    if text.font_size is not None:
        props["font-size"] = f"{_number(text.font_size)}px"
    if text.font_weight is not None:
        props["font-weight"] = text.font_weight
    if text.font_style is not None:
        props["font-style"] = text.font_style
    if text.colour is not None:
        props["color"] = text.colour
    return props


# ── foreignObject HTML ──


def _unwrap(element: Any) -> None:
    """Replace ``element`` with its own text and children (keeps document order)."""
    parent = element.getparent()
    if parent is None:
        return
    previous = element.getprevious()
    text = element.text or ""
    if previous is not None:
        previous.tail = (previous.tail or "") + text
    else:
        parent.text = (parent.text or "") + text
    index = parent.index(element)
    children = list(element)
    for offset, child in enumerate(children):
        parent.insert(index + offset, child)
    tail = element.tail or ""
    anchor = children[-1] if children else previous
    if anchor is not None:
        anchor.tail = (anchor.tail or "") + tail
    else:
        parent.text = (parent.text or "") + tail
    parent.remove(element)


def _strip_descendant_style(descendant: Any, properties: set[str]) -> None:
    declarations = parse_declarations(descendant.get("style"))
    if any(name in declarations for name in properties):
        for name in properties:
            declarations.pop(name, None)
        _set_style(descendant, declarations)
    if localname(descendant) == "font":
        for prop, attr in _FONT_ATTR_FOR_PROPERTY.items():
            if prop in properties and descendant.get(attr) is not None:
                del descendant.attrib[attr]


def strip_conflicting_markup(div: Any, properties: set[str]) -> None:
    """Remove nested formatting that would override ``properties`` set on ``div``."""
    for descendant in list(div.iter()):
        if descendant is div or not isinstance(descendant.tag, str):
            continue
        _strip_descendant_style(descendant, properties)
    unwrap_tags = set()
    for prop, tags in _UNWRAP_FOR_PROPERTY.items():
        if prop in properties:
            unwrap_tags |= tags
    for descendant in list(div.iter()):
        if descendant is not div and localname(descendant) in unwrap_tags:
            _unwrap(descendant)


def _update_drawio_colours(div: Any, colour: str) -> None:
    parent = div.getparent()
    if parent is None or parent.get("data-drawio-colors") is None:
        return
    declarations = parse_declarations(parent.get("data-drawio-colors"))
    declarations["color"] = colour
    parent.set("data-drawio-colors", format_declarations(declarations))


def style_foreign_div(div: Any, text: TextStyle) -> None:
    """Apply ``text`` to an innermost foreignObject ``<div>`` and its descendants."""
    props = css_text_properties(text)
    if not props:
        return
    declarations = parse_declarations(div.get("style"))
    declarations.update(props)
    _set_style(div, declarations)
    strip_conflicting_markup(div, set(props))
    if text.colour is not None:
        _update_drawio_colours(div, text.colour)


# ── <text> fallback ──


def style_text_element(element: Any, text: TextStyle) -> None:
    for name, value in css_text_properties(text).items():
        element.set("fill" if name == "color" else name, value)


def style_text_target(target: TextTarget, text: TextStyle) -> None:
    if target.kind is TextTargetKind.FOREIGN_OBJECT:
        style_foreign_div(target.element, text)
    else:
        style_text_element(target.element, text)


# ── Shapes ──


def _paintable(element: Any, attribute: str) -> bool:
    """Whether the template paints this attribute (explicit, not ``none``)."""
    value = element.get(attribute)
    return value is not None and value.strip().lower() != "none"


def _style_shape_element(element: Any, box: BoxStyle) -> None:
    name = localname(element)
    if name == "image":
        return
    has_stroke, has_fill = _paintable(element, "stroke"), _paintable(element, "fill")
    if not has_stroke and not has_fill:
        return  # invisible label backing: never invent a box
    if has_stroke and box.stroke is not None:
        element.set("stroke", box.stroke)
    if has_stroke and box.stroke_width is not None:
        element.set("stroke-width", _number(box.stroke_width))
    if has_fill and box.fill is not None:
        element.set("fill", box.fill)
    if name == "rect" and box.corner_radius is not None:
        element.set("rx", _number(box.corner_radius))
        element.set("ry", _number(box.corner_radius))


def style_shape(shape: ShapeRef, box: BoxStyle) -> None:
    """Restyle a slot's shape (a basic shape or a group of them)."""
    if box.is_empty():
        return
    element = shape.element
    if localname(element) in SHAPE_TAGS:
        _style_shape_element(element, box)
        return
    for child in element.iter():
        if localname(child) in SHAPE_TAGS:
            _style_shape_element(child, box)


# ── Edges ──


def _style_edge_element(element: Any, line: LineStyle) -> None:
    for path in element.iter():
        if localname(path) not in ("path", "line", "polyline", "polygon"):
            continue
        if _paintable(path, "fill"):  # arrowhead
            if line.stroke is not None:
                path.set("fill", line.stroke)
                path.set("stroke", line.stroke)
            continue
        if line.stroke is not None:
            path.set("stroke", line.stroke)
        if line.stroke_width is not None:
            path.set("stroke-width", _number(line.stroke_width))


def style_edge(edge: EdgeRef, line: LineStyle) -> None:
    if line.is_empty():
        return
    if edge.element is not None:
        _style_edge_element(edge.element, line)
    for marker in edge.markers:  # arrowheads of a bare stroke path (ordered adapter)
        _style_edge_element(marker, line)
    if edge.cell is not None:
        style = edge.cell.style_dict
        if line.stroke is not None:
            style["strokeColor"] = line.stroke
        if line.stroke_width is not None:
            style["strokeWidth"] = _number(line.stroke_width)
        edge.cell.set_style_dict(style)


# ── draw.io model styles ──


def font_style_bits(existing: str | None, text: TextStyle) -> str:
    """Set/clear bold (1) and italic (2); keep underline (4) and strikethrough (8)."""
    try:
        bits = int(existing) if existing else 0
    except ValueError:
        bits = 0
    if text.font_weight is not None:
        bits = (
            bits | FONT_STYLE_BOLD
            if text.font_weight == "bold"
            else bits & ~FONT_STYLE_BOLD
        )
    if text.font_style is not None:
        bits = (
            bits | FONT_STYLE_ITALIC
            if text.font_style == "italic"
            else bits & ~FONT_STYLE_ITALIC
        )
    return str(bits)


def style_cell_text(cell: MxCell, text: TextStyle) -> None:
    style = cell.style_dict
    if text.colour is not None:
        style["fontColor"] = text.colour
    if text.font_family is not None:
        style["fontFamily"] = text.font_family
    if text.font_size is not None:
        style["fontSize"] = _number(text.font_size)
    if text.font_weight is not None or text.font_style is not None:
        style["fontStyle"] = font_style_bits(style.get("fontStyle"), text)
    cell.set_style_dict(style)


def _cell_paints(style: dict[str, str | None], key: str) -> bool:
    """draw.io paints when the key is absent (default) or set to a colour."""
    value = style.get(key)
    if value is None:
        shape = next(iter(style), "")
        return key in style or shape not in ("text", "image")
    return value.strip().lower() != "none"


def style_cell_box(cell: MxCell, box: BoxStyle) -> None:
    style = cell.style_dict
    if "image" in style or next(iter(style), "") == "image":
        return
    paints_stroke, paints_fill = (
        _cell_paints(style, "strokeColor"),
        _cell_paints(style, "fillColor"),
    )
    if paints_stroke and box.stroke is not None:
        style["strokeColor"] = box.stroke
    if paints_stroke and box.stroke_width is not None:
        style["strokeWidth"] = _number(box.stroke_width)
    if paints_fill and box.fill is not None:
        style["fillColor"] = box.fill
    if box.corner_radius is not None and (paints_stroke or paints_fill):
        _set_cell_rounding(style, box.corner_radius)
    cell.set_style_dict(style)


def _set_cell_rounding(style: dict[str, str | None], radius: float) -> None:
    if radius > 0:
        style["rounded"] = "1"
        style["absoluteArcSize"] = "1"
        style["arcSize"] = _number(radius * 2)
    else:
        style["rounded"] = "0"
        style.pop("absoluteArcSize", None)
        style.pop("arcSize", None)


# ── Roles and the hook ──


def theme_role_for(slot: Slot, bound: bool) -> ThemeRole | None:
    """Which theme role a slot takes; ``None`` for legacy-only tokens."""
    if slot.role is SlotRole.TITLE:
        return ThemeRole.TITLE
    if slot.role is SlotRole.DATE:
        return ThemeRole.DATE
    if slot.role is SlotRole.UNKNOWN:
        return None
    if not bound:
        return ThemeRole.UNBOUND
    return ThemeRole.MODIFIER if slot.role in MODIFIER_SLOT_ROLES else ThemeRole.BOUND


def pin_light_colour_scheme(job: RenderJob) -> None:
    """Make ``light-dark()`` templates render light regardless of the OS theme (DOM only)."""
    assert job.doc is not None
    root = job.doc.root
    declarations = parse_declarations(root.get("style"))
    declarations["color-scheme"] = "light"
    root.set("style", format_declarations(declarations).strip())


class _ThemeWriter:
    """One pass over the slots; shared elements are styled once."""

    def __init__(self, job: RenderJob, theme: Theme) -> None:
        assert job.slots is not None
        self.job = job
        self.theme = theme
        self.capabilities = job.slots.capabilities
        self._seen: set[int] = set()

    def _first_visit(self, obj: Any) -> bool:
        key = id(obj)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True

    def write_slot(self, slot: Slot) -> None:
        bound = bool(self.job.resolver.text_for(slot.key))
        role = theme_role_for(slot, bound)
        if role is None:
            return
        style = self.theme.role(role)
        if Capability.TEXT_STYLE in self.capabilities:
            for target in slot.text_targets:
                if self._first_visit(target.element):
                    style_text_target(target, style.text)
        if slot.cell is not None and self._first_visit(slot.cell.element):
            style_cell_text(slot.cell, style.text)
            style_cell_box(slot.cell, style.box)
        if Capability.SHAPE_STYLE in self.capabilities and slot.shape is not None:
            if self._first_visit(slot.shape.element):
                style_shape(slot.shape, style.box)
        if Capability.EDGES in self.capabilities:
            self._write_edges(slot)

    def _write_edges(self, slot: Slot) -> None:
        for edge in slot.edges:
            anchor = edge.element if edge.element is not None else edge.cell
            if anchor is not None and self._first_visit(anchor):
                style_edge(edge, self.theme.leader_line)


def apply_theme(job: RenderJob) -> None:
    """Style hook: apply ``job.ctx.theme``; a no-op under Original (unchanged)."""
    theme = job.ctx.theme
    if theme is None or job.slots is None:
        return
    writer = _ThemeWriter(job, theme)
    for slot in job.slots.slots:
        writer.write_slot(slot)
    job.write_model()


__all__ = [
    "apply_theme",
    "css_text_properties",
    "font_style_bits",
    "format_declarations",
    "parse_declarations",
    "pin_light_colour_scheme",
    "strip_conflicting_markup",
    "style_cell_box",
    "style_cell_text",
    "style_edge",
    "style_foreign_div",
    "style_shape",
    "style_text_element",
    "theme_role_for",
]

if __name__ == "__main__":
    pass
