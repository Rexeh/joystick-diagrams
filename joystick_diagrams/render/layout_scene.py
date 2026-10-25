"""Geometry the layout stage reasons about: slot identities, the page, occupied
space and how leader lines attach to slots (plan §5.4).

``build_scene(slot_map, root, model)`` turns a ``SlotMap`` into a ``LayoutScene``:

- ``groups``: one ``SlotGroup`` per *stable slot identity* ``key#dup``.
  Slots with the same key are numbered top-to-bottom, left-to-right; stacked
  duplicates (bboxes with an intersection-over-union above 80 %, i.e. drawn on
  top of each other, not merely nested) share one group and move together. A group whose bbox covers more than a quarter of the page is
  ``background`` (the stray ``Button_22`` frame in Virpil Control Panel #1) and
  is never moved or used for collision.
- ``page``: the SVG ``viewBox`` as a ``Rect``.
- ``occupied()``: rectangles auto-add must avoid — every non-background slot
  bbox, every non-background shape (``<image>`` and anything over 25 % of the
  page are background), and thin rectangles along every leader line.
- ``attachments``: for every model edge, which slot group each end belongs to
  and how: ``"model"`` when the edge's ``source``/``target`` is the slot's cell
  or an ancestor group of it (then *every* slot under that ancestor must move by
  the same delta for the end to follow), ``"nearest"`` for a free end lying
  within 8 px of exactly one template slot (ties within 1 px attach to nothing,
  and app-added boxes are never candidates).

``GroupTransform`` describes what happened to a group (translate, resize) and
maps an attached end point from its original to its new position; resized
groups keep the end on the same relative spot of the border.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from joystick_diagrams.render.adapters._common import (
    SHAPE_TAGS,
    is_rotated,
    localname,
    rect_of,
)
from joystick_diagrams.render.adapters.edge_mapping import path_points
from joystick_diagrams.render.drawio_model import DrawioModel, MxCell
from joystick_diagrams.render.layout import STACKED_OVERLAP_RATIO, format_target
from joystick_diagrams.render.slots import EdgeRef, Rect, Slot, SlotMap, SlotRole

BACKGROUND_AREA_RATIO = 0.25
NEAREST_SLOT_DISTANCE_PX = 8.0
NEAREST_TIE_PX = 1.0
EDGE_SEGMENT_THICKNESS_PX = 2.0
CONTAINER_TOLERANCE_PX = 1.0
EDGE_SEGMENT_STEP_PX = 12.0

Point = tuple[float, float]
_VIEWBOX_RE = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", re.IGNORECASE)


# ── Slot identities ──


@dataclass
class SlotGroup:
    """One stable identity: a key plus duplicate index, holding 1+ stacked slots."""

    target: str
    key: str
    dup: int
    slots: list[Slot]
    bbox: Rect | None
    background: bool = False

    @property
    def role(self) -> SlotRole:
        return self.slots[0].role

    @property
    def input_key(self) -> str | None:
        return self.slots[0].input_key

    @property
    def modifier_index(self) -> int | None:
        return self.slots[0].modifier_index

    @property
    def rotated(self) -> bool:
        return any(slot.rotated for slot in self.slots)

    @property
    def cells(self) -> list[MxCell]:
        seen: set[str] = set()
        cells: list[MxCell] = []
        for slot in self.slots:
            if slot.cell is not None and slot.cell.id not in seen:
                seen.add(slot.cell.id or "")
                cells.append(slot.cell)
        return cells

    @property
    def movable(self) -> bool:
        return not self.background and self.bbox is not None

    @property
    def resizable(self) -> bool:
        """Only unrotated slots drawn as a single ``<rect>`` resize (plan §5.4)."""
        if self.background or self.rotated:
            return False
        return all(single_rect(slot) is not None for slot in self.slots)


def single_rect(slot: Slot) -> Any | None:
    """The one ``<rect>`` a slot's shape consists of, or ``None``."""
    if slot.shape is None:
        return None
    element = slot.shape.element
    if localname(element) == "rect":
        return None if is_rotated(element) else element
    if localname(element) != "g":
        return None
    shapes = [d for d in element.iter() if localname(d) in SHAPE_TAGS]
    if (
        len(shapes) == 1
        and localname(shapes[0]) == "rect"
        and not is_rotated(shapes[0])
    ):
        return shapes[0]
    return None


def _union(a: Rect | None, b: Rect | None) -> Rect | None:
    if a is None:
        return b
    if b is None:
        return a
    x, y = min(a.x, b.x), min(a.y, b.y)
    return Rect(x, y, max(a.right, b.right) - x, max(a.bottom, b.bottom) - y)


def _cluster_stacked(slots: list[Slot]) -> list[list[Slot]]:
    """Group slots whose bboxes overlap by more than ``STACKED_OVERLAP_RATIO``."""
    clusters: list[list[Slot]] = []
    for slot in slots:
        for cluster in clusters:
            anchor = cluster[0]
            if (
                slot.bbox is not None
                and anchor.bbox is not None
                and slot.bbox.iou(anchor.bbox) > STACKED_OVERLAP_RATIO
            ):
                cluster.append(slot)
                break
        else:
            clusters.append([slot])
    return clusters


def _position_key(indexed: tuple[int, Slot]) -> tuple[float, float, int]:
    index, slot = indexed
    if slot.bbox is None:
        return (float("inf"), float("inf"), index)
    return (round(slot.bbox.y), round(slot.bbox.x), index)


def build_slot_groups(slot_map: SlotMap, page: Rect) -> list[SlotGroup]:
    by_key: dict[str, list[tuple[int, Slot]]] = {}
    for index, slot in enumerate(slot_map.slots):
        by_key.setdefault(slot.key, []).append((index, slot))
    groups: list[SlotGroup] = []
    for key, indexed in by_key.items():
        ordered = [slot for _i, slot in sorted(indexed, key=_position_key)]
        for dup, cluster in enumerate(_cluster_stacked(ordered), start=1):
            bbox = None
            for slot in cluster:
                bbox = _union(bbox, slot.bbox)
            background = (
                bbox is not None and bbox.area > page.area * BACKGROUND_AREA_RATIO
            )
            groups.append(
                SlotGroup(format_target(key, dup), key, dup, cluster, bbox, background)
            )
    return groups


# ── Page and occupied space ──


def page_rect(root: Any) -> Rect:
    numbers = [float(n) for n in _VIEWBOX_RE.findall(root.get("viewBox") or "")]
    if len(numbers) == 4 and numbers[2] > 0 and numbers[3] > 0:
        return Rect(*numbers)
    width = _VIEWBOX_RE.search(root.get("width") or "")
    height = _VIEWBOX_RE.search(root.get("height") or "")
    return Rect(
        0.0,
        0.0,
        float(width.group(0)) if width else 800.0,
        float(height.group(0)) if height else 600.0,
    )


def shape_rects(root: Any, page: Rect, slots: list[Rect] = ()) -> list[Rect]:
    """Bboxes of every non-background basic shape (edge strokes excluded).

    Besides ``<image>`` and anything over 25 % of the page, a shape that fully
    *contains* a slot is a panel frame drawn behind labels, not an obstacle, and
    is skipped too (otherwise every slot inside a frame has no free side).
    """
    limit = page.area * BACKGROUND_AREA_RATIO
    rects: list[Rect] = []
    for element in root.iter():
        name = localname(element)
        if name not in SHAPE_TAGS or name == "image":
            continue
        if element.get("pointer-events") == "stroke":
            continue
        bbox = rect_of(element)
        if bbox is None or bbox.area > limit or bbox.area == 0:
            continue
        if any(
            bbox.contains(slot, CONTAINER_TOLERANCE_PX) and bbox.area > slot.area * 1.5
            for slot in slots
        ):
            continue  # a frame around labels
        rects.append(bbox)
    return rects


def segment_rects(
    points: list[Point], thickness: float = EDGE_SEGMENT_THICKNESS_PX
) -> list[Rect]:
    """Thin rectangles along a polyline (diagonals are chopped into short pieces)."""
    rects: list[Rect] = []
    half = thickness / 2
    for (x1, y1), (x2, y2) in zip(points, points[1:], strict=False):
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        steps = max(1, int(length // EDGE_SEGMENT_STEP_PX))
        for k in range(steps):
            ax, ay = x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps
            bx, by = x1 + (x2 - x1) * (k + 1) / steps, y1 + (y2 - y1) * (k + 1) / steps
            rects.append(
                Rect(
                    min(ax, bx) - half,
                    min(ay, by) - half,
                    abs(bx - ax) + thickness,
                    abs(by - ay) + thickness,
                )
            )
    return rects


# ── Edge attachment ──


@dataclass
class EndAttachment:
    group: str | None = None  # slot target
    kind: str | None = None  # "model" | "nearest"
    members: tuple[str, ...] = ()  # every group under the model terminal
    point: Point | None = None  # rendered end point (original)


@dataclass
class EdgeAttachment:
    edge: EdgeRef
    source: EndAttachment = field(default_factory=EndAttachment)
    target: EndAttachment = field(default_factory=EndAttachment)

    @property
    def edge_id(self) -> str | None:
        return self.edge.edge_id

    def end(self, name: str) -> EndAttachment:
        return self.source if name == "source" else self.target

    def attached_groups(self) -> set[str]:
        return {e.group for e in (self.source, self.target) if e.group is not None}


def _ancestors(cell_id: str, cells: dict[str, MxCell]) -> list[str]:
    chain: list[str] = []
    seen: set[str] = set()
    current = cells.get(cell_id)
    while current is not None and current.parent and current.parent not in seen:
        seen.add(current.parent)
        chain.append(current.parent)
        current = cells.get(current.parent)
    return chain


def _model_members(
    terminal: str, groups: list[SlotGroup], cells: dict[str, MxCell]
) -> list[str]:
    members: list[str] = []
    for group in groups:
        for cell in group.cells:
            if cell.id == terminal or terminal in _ancestors(cell.id or "", cells):
                members.append(group.target)
                break
    return members


def nearest_group(point: Point, groups: list[SlotGroup]) -> SlotGroup | None:
    """The template slot within 8 px of a point, unless two tie within 1 px."""
    ranked = sorted(
        (
            (group.bbox.distance_to_point(*point), group)
            for group in groups
            if group.bbox is not None and not group.background
        ),
        key=lambda item: item[0],
    )
    if not ranked or ranked[0][0] > NEAREST_SLOT_DISTANCE_PX:
        return None
    if len(ranked) > 1 and ranked[1][0] - ranked[0][0] < NEAREST_TIE_PX:
        return None
    return ranked[0][1]


def _attach_end(
    terminal: str | None,
    point: Point | None,
    groups: list[SlotGroup],
    cells: dict[str, MxCell],
) -> EndAttachment:
    if terminal is not None:
        members = _model_members(terminal, groups, cells)
        group = members[0] if len(members) == 1 else None
        return EndAttachment(group, "model" if members else None, tuple(members), point)
    if point is not None:
        near = nearest_group(point, groups)
        if near is not None:
            return EndAttachment(near.target, "nearest", (near.target,), point)
    return EndAttachment(point=point)


def edge_points(edge: EdgeRef) -> list[Point]:
    path = edge.stroke_path
    return path_points(path.get("d")) if path is not None else []


def build_attachments(
    edges: list[EdgeRef], groups: list[SlotGroup], cells: dict[str, MxCell]
) -> list[EdgeAttachment]:
    attachments: list[EdgeAttachment] = []
    for edge in edges:
        points = edge_points(edge)
        start = points[0] if points else None
        finish = points[-1] if points else None
        attachments.append(
            EdgeAttachment(
                edge,
                _attach_end(edge.source_id, start, groups, cells),
                _attach_end(edge.target_id, finish, groups, cells),
            )
        )
    return attachments


# ── Transforms ──


@dataclass(frozen=True)
class GroupTransform:
    """How a group changed: original bbox → new bbox (translate and/or resize)."""

    before: Rect
    after: Rect

    @property
    def delta(self) -> Point:
        return (self.after.x - self.before.x, self.after.y - self.before.y)

    def map_point(self, point: Point) -> Point:
        """Keep an attached end on the same relative spot of the (new) bbox."""
        u = (point[0] - self.before.x) / self.before.width if self.before.width else 0.0
        v = (
            (point[1] - self.before.y) / self.before.height
            if self.before.height
            else 0.0
        )
        u, v = min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0)
        return (
            self.after.x + u * self.after.width,
            self.after.y + v * self.after.height,
        )


# ── Scene ──


@dataclass
class LayoutScene:
    page: Rect
    groups: list[SlotGroup]
    attachments: list[EdgeAttachment]
    shapes: list[Rect]
    offset: tuple[float, float]
    cells: dict[str, MxCell]

    def group(self, target: str) -> SlotGroup | None:
        return self._by_target.get(target)

    def __post_init__(self) -> None:
        self._by_target = {group.target: group for group in self.groups}

    def primary_for_input(self, input_key: str, dup: int = 1) -> SlotGroup | None:
        """The action slot of an input (``button_1#dup``)."""
        return self.group(format_target(input_key, dup))

    def occupied(self, extra: list[Rect] = ()) -> list[Rect]:
        """Rectangles auto-add must avoid (deduplicated, in a stable order)."""
        rects = [g.bbox for g in self.groups if g.bbox is not None and not g.background]
        rects.extend(self.shapes)
        for attachment in self.attachments:
            rects.extend(segment_rects(edge_points(attachment.edge)))
        rects.extend(extra)
        return list(dict.fromkeys(rects))


def build_scene(slot_map: SlotMap, root: Any, model: DrawioModel) -> LayoutScene:
    page = page_rect(root)
    groups = build_slot_groups(slot_map, page)
    cells = model.cells_by_id()
    slot_rects = [g.bbox for g in groups if g.bbox is not None and not g.background]
    return LayoutScene(
        page=page,
        groups=groups,
        attachments=build_attachments(slot_map.edges, groups, cells),
        shapes=shape_rects(root, page, slot_rects),
        offset=slot_map.offset or (0.0, 0.0),
        cells=cells,
    )


__all__ = [
    "BACKGROUND_AREA_RATIO",
    "NEAREST_SLOT_DISTANCE_PX",
    "EdgeAttachment",
    "EndAttachment",
    "GroupTransform",
    "LayoutScene",
    "SlotGroup",
    "build_attachments",
    "build_scene",
    "build_slot_groups",
    "edge_points",
    "nearest_group",
    "page_rect",
    "segment_rects",
    "shape_rects",
    "single_rect",
]

if __name__ == "__main__":
    pass
