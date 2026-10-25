"""Helpers shared by the draw.io adapters: label-group discovery, shapes, bboxes.

draw.io renders every label as::

    <g transform="translate(-0.5 -0.5)">            ← the *label group* (container)
      <switch>
        <foreignObject …><div xmlns="xhtml">…<div style="display: inline-block…">TOKEN</div></div></foreignObject>
        <text …>TOKEN</text>                        ← fallback for non-HTML renderers
      </switch>
    </g>

The shape drawn behind it is the preceding sibling (flat files), the preceding
``<g>`` of the wrapping per-cell group (grouped files) or the first child group
of ``g[@data-cell-id]`` (cell-id files). ``find_shape`` walks up from the label
group until it finds a preceding element, which covers all three layouts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from joystick_diagrams.render.drawio_model import MxCell
from joystick_diagrams.render.slots import (
    Rect,
    ShapeRef,
    Slot,
    TextTarget,
    TextTargetKind,
)
from joystick_diagrams.render.tokens import classify, find_tokens

SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
SVG = f"{{{SVG_NS}}}"
XHTML = f"{{{XHTML_NS}}}"

SHAPE_TAGS = frozenset(
    {"rect", "ellipse", "circle", "path", "image", "polygon", "polyline", "line"}
)
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", re.IGNORECASE)
GEOMETRY_TOLERANCE_PX = 3.0


def localname(element: Any) -> str:
    return etree.QName(element).localname if isinstance(element.tag, str) else ""


def _float(value: str | None) -> float:
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0


# ── Label groups ──


@dataclass
class LabelGroup:
    container: Any  # the <g transform="translate(…)"> around <switch>
    switch: Any
    foreign_object: Any | None
    text_element: Any | None
    tokens: list[str] = field(default_factory=list)  # lower-cased
    norm_text: str = ""  # whitespace-collapsed casefolded visible text


def _innermost_divs(foreign_object: Any) -> list[Any]:
    """The xhtml ``<div>``s without ``<div>`` children (the inline-block text box)."""
    return [
        div
        for div in foreign_object.iter(f"{XHTML}div")
        if div.find(f"{XHTML}div") is None
    ]


def _visible_text(element: Any) -> str:
    return " ".join(" ".join(element.itertext()).split()).casefold()


def label_group_from_switch(switch: Any) -> LabelGroup | None:
    foreign_object = switch.find(f"{SVG}foreignObject")
    text_element = switch.find(f"{SVG}text")
    if foreign_object is None and text_element is None:
        return None
    source = foreign_object if foreign_object is not None else text_element
    joined = " ".join(source.itertext())
    return LabelGroup(
        container=switch.getparent(),
        switch=switch,
        foreign_object=foreign_object,
        text_element=text_element,
        tokens=find_tokens(joined),
        norm_text=_visible_text(source),
    )


def iter_label_groups(root: Any) -> list[LabelGroup]:
    """Every rendered label in document order (draw.io's trailing banner is skipped)."""
    groups: list[LabelGroup] = []
    for switch in root.iter(f"{SVG}switch"):
        group = label_group_from_switch(switch)
        if group is not None:
            groups.append(group)
    return groups


def text_targets(group: LabelGroup) -> list[TextTarget]:
    targets: list[TextTarget] = []
    if group.foreign_object is not None:
        targets.extend(
            TextTarget(div, TextTargetKind.FOREIGN_OBJECT)
            for div in _innermost_divs(group.foreign_object)
        )
    if group.text_element is not None:
        targets.append(TextTarget(group.text_element, TextTargetKind.TEXT))
    return targets


# ── Shapes and geometry ──


def _path_bbox(d: str | None) -> Rect | None:
    numbers = [float(n) for n in _NUMBER_RE.findall(d or "")]
    if len(numbers) < 4:
        return None
    xs, ys = numbers[0::2], numbers[1::2]
    return Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


_ROTATE_RE = re.compile(
    r"rotate\(\s*(-?[\d.]+)(?:[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+))?\s*\)"
)


def rotation_of(element: Any) -> tuple[float, float, float] | None:
    """``(angle, cx, cy)`` of a ``rotate(...)`` in the element's ``transform``."""
    match = _ROTATE_RE.search(element.get("transform") or "")
    if match is None:
        return None
    angle = float(match.group(1))
    cx = float(match.group(2)) if match.group(2) is not None else 0.0
    cy = float(match.group(3)) if match.group(3) is not None else 0.0
    return angle, cx, cy


def is_rotated(element: Any) -> bool:
    rotation = rotation_of(element)
    return rotation is not None and rotation[0] % 360 != 0


def rotated_bbox(rect: Rect, angle: float, cx: float, cy: float) -> Rect:
    """Axis-aligned bounds of ``rect`` rotated by ``angle`` degrees around (cx, cy)."""
    import math

    theta = math.radians(angle)
    cos, sin = math.cos(theta), math.sin(theta)
    xs: list[float] = []
    ys: list[float] = []
    for px, py in (
        (rect.x, rect.y),
        (rect.right, rect.y),
        (rect.x, rect.bottom),
        (rect.right, rect.bottom),
    ):
        dx, dy = px - cx, py - cy
        xs.append(cx + dx * cos - dy * sin)
        ys.append(cy + dx * sin + dy * cos)
    return Rect(
        round(min(xs), 4),
        round(min(ys), 4),
        round(max(xs) - min(xs), 4),
        round(max(ys) - min(ys), 4),
    )


def rect_of(element: Any) -> Rect | None:
    """Bounding box of a basic shape element, in rendered coordinates.

    A ``transform="rotate(a,cx,cy)"`` on the element (draw.io's rotated or
    ``direction=south`` cells) is applied, so the bbox is where the shape is seen.
    """
    rect = _untransformed_rect_of(element)
    rotation = rotation_of(element)
    if rect is None or rotation is None:
        return rect
    return rotated_bbox(rect, *rotation)


def _untransformed_rect_of(element: Any) -> Rect | None:
    name = localname(element)
    if name in ("rect", "image"):
        return Rect(
            _float(element.get("x")),
            _float(element.get("y")),
            _float(element.get("width")),
            _float(element.get("height")),
        )
    if name == "ellipse":
        rx, ry = _float(element.get("rx")), _float(element.get("ry"))
        return Rect(
            _float(element.get("cx")) - rx,
            _float(element.get("cy")) - ry,
            2 * rx,
            2 * ry,
        )
    if name == "circle":
        r = _float(element.get("r"))
        return Rect(
            _float(element.get("cx")) - r, _float(element.get("cy")) - r, 2 * r, 2 * r
        )
    if name == "path":
        return _path_bbox(element.get("d"))
    return None


def shape_from(candidate: Any) -> ShapeRef | None:
    """A ``ShapeRef`` when ``candidate`` is a shape or a group of shapes (no labels)."""
    name = localname(candidate)
    if name in SHAPE_TAGS:
        return ShapeRef(candidate, rect_of(candidate))
    if name == "g" and candidate.find(f".//{SVG}switch") is None:
        shapes = [d for d in candidate.iter() if localname(d) in SHAPE_TAGS]
        if shapes:
            return ShapeRef(candidate, rect_of(shapes[0]))
    return None


def _previous_element(element: Any) -> Any | None:
    prev = element.getprevious()
    while prev is not None and not isinstance(prev.tag, str):
        prev = prev.getprevious()
    return prev


def find_shape(container: Any, stop: Any | None = None) -> ShapeRef | None:
    """The element drawn just before a label group, climbing out of wrapper groups."""
    element = container
    while element is not None and element is not stop:
        prev = _previous_element(element)
        if prev is not None:
            return shape_from(prev)
        parent = element.getparent()
        if parent is None or localname(parent) not in ("g", "a"):
            return None
        element = parent
    return None


def absolute_geometry(cell: MxCell, cells: dict[str, MxCell] | None) -> Rect | None:
    """A vertex's geometry in page coordinates (ancestor group origins added).

    draw.io stores a child's geometry relative to its parent group; ``cells``
    (``model.cells_by_id()``) lets the chain be resolved. Without it the raw
    geometry is returned.
    """
    geometry = cell.geometry
    if geometry is None:
        return None
    x, y = geometry.x, geometry.y
    parent_id = cell.parent
    seen: set[str] = set()
    while cells and parent_id and parent_id not in seen:
        seen.add(parent_id)
        parent = cells.get(parent_id)
        if parent is None or not parent.is_vertex or parent.geometry is None:
            break
        x += parent.geometry.x
        y += parent.geometry.y
        parent_id = parent.parent
    return Rect(x, y, geometry.width, geometry.height)


def cell_origin(cell: MxCell, cells: dict[str, MxCell] | None) -> tuple[float, float]:
    """Page offset of the coordinate system a cell's geometry (and edge points) use."""
    x = y = 0.0
    parent_id = cell.parent
    seen: set[str] = set()
    while cells and parent_id and parent_id not in seen:
        seen.add(parent_id)
        parent = cells.get(parent_id)
        if parent is None or not parent.is_vertex or parent.geometry is None:
            break
        x += parent.geometry.x
        y += parent.geometry.y
        parent_id = parent.parent
    return x, y


def geometry_matches(
    shape: ShapeRef | None,
    cell: MxCell | None,
    offset,
    cells: dict[str, MxCell] | None = None,
) -> bool:
    """Whether a shape sits where the model geometry (plus offset) says, within ±3 px."""
    if shape is None or shape.bbox is None or cell is None or offset is None:
        return False
    geometry = absolute_geometry(cell, cells)
    if geometry is None:
        return False
    dx, dy = offset
    return (
        abs(shape.bbox.x - (geometry.x + dx)) <= GEOMETRY_TOLERANCE_PX
        and abs(shape.bbox.y - (geometry.y + dy)) <= GEOMETRY_TOLERANCE_PX
    )


def offset_rect(rect: Rect | None, offset) -> Rect | None:
    if rect is None or offset is None:
        return None
    return Rect(rect.x + offset[0], rect.y + offset[1], rect.width, rect.height)


# ── Slots ──


def make_slot(group: LabelGroup, cell: MxCell | None, shape: ShapeRef | None) -> Slot:
    info = classify(group.tokens[0])
    return Slot(
        key=info.token,
        role=info.role,
        input_key=info.input_key,
        modifier_index=info.modifier_index,
        tokens=tuple(group.tokens),
        label_group=group.container,
        text_targets=text_targets(group),
        cell=cell,
        shape=shape,
        bbox=shape.bbox if shape is not None else None,
        rotated=slot_is_rotated(group, cell, shape),
    )


def slot_is_rotated(
    group: LabelGroup, cell: MxCell | None, shape: ShapeRef | None
) -> bool:
    """Rotated via the model style, the label transform or the shape transform."""
    if cell is not None and cell.rotation:
        return True
    if is_rotated(group.container):
        return True
    if shape is not None:
        if is_rotated(shape.element):
            return True
        if localname(shape.element) == "g" and any(
            is_rotated(child)
            for child in shape.element.iter()
            if localname(child) in SHAPE_TAGS
        ):
            return True
    return False


if __name__ == "__main__":
    pass
