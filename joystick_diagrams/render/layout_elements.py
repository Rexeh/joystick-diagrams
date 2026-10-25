"""DOM and model builders used by the layout stage (plan §5.4).

Everything here edits lxml elements or draw.io cells in place; nothing here
decides *what* to change (that is ``layout_apply.py``). The rendered side
follows draw.io's own output conventions so the result looks native:

- a label is ``<g transform="translate(-0.5 -0.5)"><switch><foreignObject>
  <div style="display: flex; … width: W-2px; padding-top: CYpx; margin-left:
  X+1px"><div data-drawio-colors="…"><div style="display: inline-block;
  font-size: Spx …">TEXT</div></div></div></foreignObject><text x="CX"
  y="CY+0.3S" …>TEXT</text></switch></g>``;
- a move wraps the slot's shape(s) and label in ``<g transform="translate(dx
  dy)">`` so rotated shapes keep their own rotation centre;
- a hide wraps them in ``<g display="none">``;
- the model mirror edits ``mxGeometry`` (x/y/width/height), terminal
  ``mxPoint``s and ``visible``, and new cells get ``id="jd-<uid>"`` plus
  ``jdAdded=1`` in their style so draw.io users can tell them apart.
"""

from __future__ import annotations

import copy
import html
import re
from dataclasses import dataclass
from typing import Any

from lxml import etree

from joystick_diagrams.render.adapters._common import (
    SVG,
    SVG_NS,
    XHTML,
    XHTML_NS,
    localname,
)
from joystick_diagrams.render.drawio_model import DrawioModel, MxCell, format_style
from joystick_diagrams.render.layout import NoteStyle
from joystick_diagrams.render.slots import Rect
from joystick_diagrams.render.style_writer import (
    format_declarations,
    parse_declarations,
)

_PX_RE = re.compile(r"(-?\d+(?:\.\d+)?)px")
DEFAULT_FONT_SIZE = 12.0
MIN_FONT_SIZE = 7.0
TEXT_BASELINE_RATIO = 0.3  # draw.io: <text y> = centre y + 0.3 × font size
ADDED_CELL_PREFIX = "jd-"


def fmt(value: float) -> str:
    return f"{round(value, 2):g}"


# ── Wrapping ──


def slot_nodes(slot: Any) -> list[Any]:
    """The sibling nodes that make up a slot: its shape and the label (or wrapper)."""
    label = slot.label_group
    shape = slot.shape.element if slot.shape is not None else None
    if shape is None or label is None:
        return [node for node in (shape, label) if node is not None]
    parent = shape.getparent()
    node = label
    while node is not None and node.getparent() is not parent:
        node = node.getparent()
    label_top = node if node is not None else label
    if label_top is shape or shape in list(label_top.iter()):
        return [label_top]
    return [shape, label_top]


def wrap_nodes(nodes: list[Any], attributes: dict[str, str]) -> Any:
    """Wrap sibling ``nodes`` in a new ``<g>`` at the position of the first one."""
    parent = nodes[0].getparent()
    ordered = sorted(nodes, key=parent.index)
    wrapper = etree.Element(f"{SVG}g")
    for name, value in attributes.items():
        wrapper.set(name, value)
    parent.insert(parent.index(ordered[0]), wrapper)
    for node in ordered:
        tail = node.tail
        node.tail = None
        wrapper.append(node)
        if tail and tail.strip():
            wrapper.tail = (wrapper.tail or "") + tail
    return wrapper


def translate_value(dx: float, dy: float) -> str:
    return f"translate({fmt(dx)} {fmt(dy)})"


def prepend_translate(element: Any, dx: float, dy: float) -> None:
    """Apply a translation to an element that may already carry a transform."""
    existing = element.get("transform")
    value = translate_value(dx, dy)
    element.set("transform", f"{value} {existing}" if existing else value)


def hide_element(element: Any) -> None:
    element.set("display", "none")


# ── Shapes and labels ──


def resize_rect(rect: Any, width: float, height: float) -> None:
    rect.set("width", fmt(width))
    rect.set("height", fmt(height))


def outer_div(label_group: Any) -> Any | None:
    foreign = label_group.find(f".//{SVG}foreignObject")
    return foreign.find(f"{XHTML}div") if foreign is not None else None


def inner_div(label_group: Any) -> Any | None:
    """The innermost xhtml ``<div>`` (the inline-block text box)."""
    divs = [
        div
        for div in label_group.iter(f"{XHTML}div")
        if div.find(f"{XHTML}div") is None
    ]
    return divs[0] if divs else None


def text_element(label_group: Any) -> Any | None:
    return label_group.find(f".//{SVG}text")


def _px(declarations: dict[str, str], name: str) -> float | None:
    match = _PX_RE.search(declarations.get(name, ""))
    return float(match.group(1)) if match else None


def _set_px(declarations: dict[str, str], name: str, value: float) -> None:
    declarations[name] = f"{fmt(value)}px"


def label_font_size(label_group: Any) -> float:
    div = inner_div(label_group)
    if div is not None:
        size = _px(parse_declarations(div.get("style")), "font-size")
        if size:
            return size
    text = text_element(label_group)
    if text is not None:
        match = _PX_RE.search(text.get("font-size") or "")
        if match:
            return float(match.group(1))
    return DEFAULT_FONT_SIZE


def relayout_label(label_group: Any, dw: float, dh: float) -> None:
    """Follow a top-left anchored resize: the label centre moves by (dw/2, dh/2)."""
    div = outer_div(label_group)
    if div is not None:
        declarations = parse_declarations(div.get("style"))
        width = _px(declarations, "width")
        if width is not None:
            _set_px(declarations, "width", width + dw)
        top = _px(declarations, "padding-top")
        if top is not None:
            _set_px(declarations, "padding-top", top + dh / 2)
        div.set("style", format_declarations(declarations))
    text = text_element(label_group)
    if text is not None:
        text.set("x", fmt(float(text.get("x") or 0) + dw / 2))
        text.set("y", fmt(float(text.get("y") or 0) + dh / 2))


def place_label(label_group: Any, rect: Rect, font_size: float) -> None:
    """Centre a label inside ``rect`` (draw.io's align=center/verticalAlign=middle)."""
    cx, cy = rect.centre
    div = outer_div(label_group)
    if div is not None:
        declarations = parse_declarations(div.get("style"))
        declarations["display"] = "flex"
        declarations["align-items"] = "unsafe center"
        declarations["justify-content"] = "unsafe center"
        _set_px(declarations, "width", rect.width - 2)
        declarations["height"] = "1px"
        _set_px(declarations, "padding-top", cy)
        _set_px(declarations, "margin-left", rect.x + 1)
        div.set("style", format_declarations(declarations))
    inner = inner_div(label_group)
    if inner is not None:
        declarations = parse_declarations(inner.get("style"))
        _set_px(declarations, "font-size", font_size)
        inner.set("style", format_declarations(declarations))
    text = text_element(label_group)
    if text is not None:
        text.set("x", fmt(cx))
        text.set("y", fmt(cy + font_size * TEXT_BASELINE_RATIO))
        text.set("font-size", f"{fmt(font_size)}px")
        text.set("text-anchor", "middle")


def set_label_text(label_group: Any, text: str) -> None:
    inner = inner_div(label_group)
    if inner is not None:
        for child in list(inner):
            inner.remove(child)
        inner.text = text
    element = text_element(label_group)
    if element is not None:
        for child in list(element):
            element.remove(child)
        element.text = text


def clone_box(
    parent_slot: Any, rect: Rect, token: str, font_size: float
) -> tuple[Any, Any]:
    """A new ``(shape, label)`` pair that looks like ``parent_slot`` at ``rect``."""
    shape = _clone_shape(parent_slot, rect)
    label = copy.deepcopy(parent_slot.label_group)
    label.tail = None
    label.set("transform", "translate(-0.5 -0.5)")
    for attribute in [a for a in label.attrib if a.startswith("data-jd-")]:
        del label.attrib[attribute]
    place_label(label, rect, font_size)
    set_label_text(label, token)
    return shape, label


def _clone_shape(parent_slot: Any, rect: Rect) -> Any:
    source = None
    if parent_slot.shape is not None:
        candidates = [
            e
            for e in parent_slot.shape.element.iter()
            if localname(e) == "rect" and e.get("pointer-events") != "stroke"
        ]
        source = candidates[0] if candidates else None
    if source is not None:
        shape = copy.deepcopy(source)
        shape.tail = None
        shape.attrib.pop("transform", None)
        for attribute in [a for a in shape.attrib if a.startswith("data-jd-")]:
            del shape.attrib[attribute]
        if (shape.get("fill") or "none") == "none" and (
            shape.get("stroke") or "none"
        ) == "none":
            shape.set("stroke", "#000000")  # an invisible backing would hide the box
    else:
        shape = etree.Element(f"{SVG}rect")
        shape.set("fill", "#ffffff")
        shape.set("stroke", "#000000")
        shape.set("rx", "2")
        shape.set("ry", "2")
        shape.set("pointer-events", "all")
    shape.set("x", fmt(rect.x))
    shape.set("y", fmt(rect.y))
    resize_rect(shape, rect.width, rect.height)
    return shape


def build_label(rect: Rect, text: str, style: NoteStyle) -> Any:
    """A fresh draw.io style label group centred in ``rect``."""
    weight = "font-weight: bold; " if style.bold else ""
    align = style.align
    justify = {"left": "flex-start", "center": "center", "right": "flex-end"}[align]
    cx, cy = rect.centre
    bold_attribute = ' font-weight="bold"' if style.bold else ""
    markup = (
        f'<g xmlns="{SVG_NS}" transform="translate(-0.5 -0.5)"><switch>'
        '<foreignObject pointer-events="none" width="100%" height="100%" '
        'requiredFeatures="http://www.w3.org/TR/SVG11/feature#Extensibility" '
        'style="overflow: visible; text-align: left;">'
        f'<div xmlns="{XHTML_NS}" style="display: flex; align-items: unsafe center; '
        f"justify-content: unsafe {justify}; width: {fmt(rect.width - 2)}px; height: 1px; "
        f'padding-top: {fmt(cy)}px; margin-left: {fmt(rect.x + 1)}px;">'
        f'<div data-drawio-colors="color: {style.colour}; " '
        f'style="box-sizing: border-box; font-size: 0px; text-align: {align};">'
        f'<div style="display: inline-block; font-size: {fmt(style.font_size)}px; '
        f"font-family: {style.font_family}; color: {style.colour}; line-height: 1.2; "
        f'{weight}pointer-events: all; white-space: normal; overflow-wrap: normal;">'
        f"{html.escape(text, quote=False)}</div></div></div></foreignObject>"
        f'<text x="{fmt(cx)}" y="{fmt(cy + style.font_size * TEXT_BASELINE_RATIO)}" '
        f'fill="{style.colour}" font-family="{style.font_family}" '
        f'font-size="{fmt(style.font_size)}px" text-anchor="middle"'
        f"{bold_attribute}>"
        f"{html.escape(text, quote=False)}</text></switch></g>"
    )
    return etree.fromstring(markup)


def build_note(rect: Rect, text: str, style: NoteStyle) -> tuple[Any | None, Any]:
    shape = None
    if style.fill is not None or style.stroke is not None:
        shape = etree.Element(f"{SVG}rect")
        shape.set("x", fmt(rect.x))
        shape.set("y", fmt(rect.y))
        resize_rect(shape, rect.width, rect.height)
        shape.set("fill", style.fill or "none")
        shape.set("stroke", style.stroke or "none")
        shape.set("pointer-events", "all")
    return shape, build_label(rect, text, style)


# ── Model mirror ──


def geometry_element(cell: MxCell) -> Any | None:
    return cell.element.find("mxGeometry")


def shift_geometry(cell: MxCell, dx: float, dy: float) -> None:
    geometry = geometry_element(cell)
    if geometry is None:
        return
    geometry.set("x", fmt(float(geometry.get("x") or 0) + dx))
    geometry.set("y", fmt(float(geometry.get("y") or 0) + dy))


def set_geometry_size(cell: MxCell, width: float, height: float) -> None:
    geometry = geometry_element(cell)
    if geometry is None:
        return
    geometry.set("width", fmt(width))
    geometry.set("height", fmt(height))


def shift_terminal_point(
    cell: MxCell,
    end: str,
    delta: tuple[float, float],
    fallback: tuple[float, float] | None = None,
) -> None:
    """Move ``sourcePoint``/``targetPoint`` of an edge cell by ``delta``.

    When the geometry has no such point yet, ``fallback`` (the end's current
    position in model coordinates) is used to create one, so draw.io keeps the
    free end where the rendered line now ends.
    """
    geometry = geometry_element(cell)
    if geometry is None:
        return
    name = "sourcePoint" if end == "source" else "targetPoint"
    for point in geometry.findall("mxPoint"):
        if point.get("as") == name:
            point.set("x", fmt(float(point.get("x") or 0) + delta[0]))
            point.set("y", fmt(float(point.get("y") or 0) + delta[1]))
            return
    if fallback is not None:
        point = etree.SubElement(geometry, "mxPoint")
        point.set("x", fmt(fallback[0] + delta[0]))
        point.set("y", fmt(fallback[1] + delta[1]))
        point.set("as", name)


def set_cell_hidden(cell: MxCell) -> None:
    cell.element.set("visible", "0")


@dataclass(frozen=True)
class NewCell:
    """What a new draw.io vertex needs: id, label, style, geometry (model coords), parent."""

    cell_id: str
    value: str
    style: dict[str, str | None]
    geometry: Rect
    parent_id: str = "1"


def add_model_cell(
    model: DrawioModel, spec: NewCell, after: MxCell | None = None
) -> MxCell:
    """Append a vertex cell (``jdAdded=1``) to the model, after ``after`` if given."""
    style = dict(spec.style)
    style["jdAdded"] = "1"
    element = etree.Element("mxCell")
    element.set("id", spec.cell_id)
    element.set("value", spec.value)
    element.set("style", format_style(style))
    element.set("vertex", "1")
    element.set("parent", spec.parent_id)
    mx_geometry = etree.SubElement(element, "mxGeometry")
    mx_geometry.set("x", fmt(spec.geometry.x))
    mx_geometry.set("y", fmt(spec.geometry.y))
    mx_geometry.set("width", fmt(spec.geometry.width))
    mx_geometry.set("height", fmt(spec.geometry.height))
    mx_geometry.set("as", "geometry")
    root = model.graph.find("root")
    if root is None:
        root = model.graph
    anchor = None
    if after is not None:
        anchor = after.wrapper if after.wrapper is not None else after.element
    if anchor is not None and anchor.getparent() is root:
        root.insert(root.index(anchor) + 1, element)
    else:
        root.append(element)
    return MxCell(element, None)


__all__ = [
    "ADDED_CELL_PREFIX",
    "MIN_FONT_SIZE",
    "NewCell",
    "add_model_cell",
    "build_label",
    "build_note",
    "clone_box",
    "fmt",
    "hide_element",
    "inner_div",
    "label_font_size",
    "outer_div",
    "place_label",
    "prepend_translate",
    "relayout_label",
    "resize_rect",
    "set_cell_hidden",
    "set_geometry_size",
    "set_label_text",
    "shift_geometry",
    "shift_terminal_point",
    "slot_nodes",
    "text_element",
    "translate_value",
    "wrap_nodes",
]

if __name__ == "__main__":
    pass
