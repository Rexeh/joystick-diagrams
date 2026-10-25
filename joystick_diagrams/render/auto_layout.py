"""Automatic placement of modifier boxes (plan §5.4 auto-add, spike S6).

Given a ``LayoutScene`` and how many boxes each input needs, ``plan_auto_add``
finds non-overlapping places for them and returns *explicit*
``AddModifierBoxesOp``s (geometry relative to the parent slot) plus the boxes it
could not place. Nothing is drawn here; ``layout_apply`` renders the ops like
any other.

Algorithm (deterministic, greedy)
---------------------------------
Inputs are processed in natural key order (``button_1``, ``button_2``, …,
``button_10``, ``axis_x``, ``pov_1_u``). Boxes are sized relative to the parent
slot (``scale``, default 0.85). When the parent has a free strip below or above
it, all boxes go there as one compact row sharing the parent's width (each at
least 40 px wide). Otherwise boxes are chained: box 1 is placed next to the
parent, box 2 next to box 1, and so on, so a stack grows away from the parent.
For each box the candidate positions are tried in order:

1. the direction the previous box used (keeps the stack straight), then the
   preferred ``arrangement`` and the remaining directions. ``"auto"`` ranks the
   four directions by how much free run the parent has on that side;
2. per direction, three alignments (below/above: left-, right-aligned, centred;
   right/left: top-, bottom-aligned, centred);
3. anchors: the previous box, then the parent, then every earlier box.

A candidate is accepted when it lies inside the page and, expanded by
``gap - 0.5`` px, intersects none of the occupied rectangles: slot bboxes,
non-background shapes, leader-line segments and boxes placed so far. When no
aligned candidate fits, a proximity search tries grid positions (half a box
apart) within 2.5 box widths of the parent on every side, nearest first; then the box is
shrunk to 80 %, 64 % and 50 % (never below 28 × 11 px) and both searches run
again. After that it is reported in ``AutoAddResult.unplaced`` with reason
``"no_space"``. Other reasons: ``"parent_missing"`` (no such slot on this
template) and ``"parent_background"`` (the slot is a page-sized frame).

Usage::

    scene = build_scene(slot_map, doc.root, model)
    result = plan_auto_add(
        scene, {"button_1": 3, "axis_x": 2}, PlanOptions(arrangement="below")
    )
    for op in result.ops:
        layout_service.append_op(template_key, layer, op, content_hash)

``auto_add_for_template(raw_svg, counts, …)`` is the convenience wrapper that
parses the template and builds the scene; ``counts_from_device(device, max)``
derives the per-input counts from a device's bound modifiers.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from joystick_diagrams.render.layout import (
    DEFAULT_BOX_GAP,
    DEFAULT_BOX_SCALE,
    DEFAULT_MAX_BOXES,
    AddModifierBoxesOp,
    Arrangement,
    BoxGeometry,
    new_uid,
    parse_target,
)
from joystick_diagrams.render.layout_scene import LayoutScene, SlotGroup
from joystick_diagrams.render.slots import Rect

DIRECTIONS: tuple[str, ...] = ("below", "right", "left", "above")
SHRINK_STEPS: tuple[float, ...] = (1.0, 0.8, 0.64, 0.5)
MIN_BOX_WIDTH = 28.0
MIN_ROW_BOX_WIDTH = 40.0  # a compact row of boxes under the parent needs this per box
MIN_BOX_HEIGHT = 11.0
SEARCH_RADIUS_BOXES = 2.5  # proximity search window, in box sizes around the parent
PAGE_MARGIN = 1.0
_NATURAL_RE = re.compile(r"(\d+)")


def natural_key(text: str) -> tuple:
    return tuple(
        int(part) if part.isdigit() else part for part in _NATURAL_RE.split(text)
    )


# ── Results ──


@dataclass(frozen=True)
class PlannedBox:
    target: str  # parent slot target
    index: int
    rect: Rect
    uid: str


@dataclass(frozen=True)
class Unplaced:
    target: str
    index: int
    reason: str  # "no_space" | "parent_missing" | "parent_background"


@dataclass
class AutoAddResult:
    ops: list[AddModifierBoxesOp] = field(default_factory=list)
    placed: list[PlannedBox] = field(default_factory=list)
    unplaced: list[Unplaced] = field(default_factory=list)

    @property
    def requested(self) -> int:
        return len(self.placed) + len(self.unplaced)

    def overlaps(self, occupied: Iterable[Rect]) -> int:
        """Independent check: placed boxes intersecting ``occupied`` or each other."""
        rects = [box.rect for box in self.placed]
        count = sum(1 for r in rects for o in occupied if r.intersects(o, 0.01))
        count += sum(
            1
            for i, a in enumerate(rects)
            for b in rects[i + 1 :]
            if a.intersects(b, 0.01)
        )
        return count


# ── Candidates ──


def _aligned(
    anchor: Rect, direction: str, w: float, h: float, gap: float
) -> list[Rect]:
    if direction == "below":
        y = anchor.bottom + gap
        xs = (anchor.x, anchor.right - w, anchor.x + (anchor.width - w) / 2)
        return [Rect(x, y, w, h) for x in xs]
    if direction == "above":
        y = anchor.y - gap - h
        xs = (anchor.x, anchor.right - w, anchor.x + (anchor.width - w) / 2)
        return [Rect(x, y, w, h) for x in xs]
    if direction == "right":
        x = anchor.right + gap
        ys = (anchor.y, anchor.bottom - h, anchor.y + (anchor.height - h) / 2)
        return [Rect(x, y, w, h) for y in ys]
    x = anchor.x - gap - w
    ys = (anchor.y, anchor.bottom - h, anchor.y + (anchor.height - h) / 2)
    return [Rect(x, y, w, h) for y in ys]


def _free_run(parent: Rect, direction: str, occupied: list[Rect], page: Rect) -> float:
    """Distance from the parent's side to the nearest obstacle in that direction."""
    if direction == "below":
        limit = page.bottom - parent.bottom
        blockers = [
            o.y - parent.bottom
            for o in occupied
            if o.y >= parent.bottom and _spans_x(o, parent)
        ]
    elif direction == "above":
        limit = parent.y - page.y
        blockers = [
            parent.y - o.bottom
            for o in occupied
            if o.bottom <= parent.y and _spans_x(o, parent)
        ]
    elif direction == "right":
        limit = page.right - parent.right
        blockers = [
            o.x - parent.right
            for o in occupied
            if o.x >= parent.right and _spans_y(o, parent)
        ]
    else:
        limit = parent.x - page.x
        blockers = [
            parent.x - o.right
            for o in occupied
            if o.right <= parent.x and _spans_y(o, parent)
        ]
    return min([limit, *blockers])


def _spans_x(a: Rect, b: Rect) -> bool:
    return a.x < b.right and b.x < a.right


def _spans_y(a: Rect, b: Rect) -> bool:
    return a.y < b.bottom and b.y < a.bottom


def direction_order(
    parent: Rect, arrangement: Arrangement, occupied: list[Rect], page: Rect
) -> list[str]:
    if arrangement != "auto":
        return [arrangement, *[d for d in DIRECTIONS if d != arrangement]]
    runs = {d: _free_run(parent, d, occupied, page) for d in DIRECTIONS}
    return sorted(DIRECTIONS, key=lambda d: (-runs[d], DIRECTIONS.index(d)))


def fits(candidate: Rect, occupied: list[Rect], page: Rect, clearance: float) -> bool:
    if not page.expanded(-PAGE_MARGIN).contains(candidate):
        return False
    padded = candidate.expanded(clearance)
    return not any(padded.intersects(o) for o in occupied)


# ── Planning ──


@dataclass
class _Planner:
    page: Rect
    occupied: list[Rect]
    gap: float

    @property
    def clearance(self) -> float:
        return max(self.gap - 0.5, 0.0)

    def place_aligned(
        self, anchors: list[Rect], directions: list[str], w: float, h: float
    ) -> tuple[Rect, str] | None:
        """First aligned candidate (anchor × direction × alignment) that fits."""
        for anchor in anchors:
            for direction in directions:
                for candidate in _aligned(anchor, direction, w, h, self.gap):
                    if fits(candidate, self.occupied, self.page, self.clearance):
                        return candidate, direction
        return None

    def place_nearby(self, parent: Rect, w: float, h: float) -> Rect | None:
        """Closest free spot on a grid around the parent (deterministic order)."""
        step_x, step_y = max(w / 2, 4.0), max(h / 2, 4.0)
        reach = SEARCH_RADIUS_BOXES * max(w, h)  # same reach on every side
        window = Rect(
            parent.x - reach,
            parent.y - reach,
            parent.width + 2 * reach,
            parent.height + 2 * reach,
        )
        cx, cy = parent.centre
        candidates: list[tuple[float, float, float, Rect]] = []
        y = window.y
        while y + h <= window.bottom:
            x = window.x
            while x + w <= window.right:
                rect = Rect(round(x, 2), round(y, 2), w, h)
                rx, ry = rect.centre
                distance = ((rx - cx) ** 2 + (ry - cy) ** 2) ** 0.5
                candidates.append((distance, ry, rx, rect))
                x += step_x
            y += step_y
        for _distance, _ry, _rx, rect in sorted(candidates):
            if fits(rect, self.occupied, self.page, self.clearance):
                return rect
        return None

    def place_one(
        self,
        parent: Rect,
        anchors: list[Rect],
        directions: list[str],
        size: tuple[float, float],
    ) -> tuple[Rect, str | None] | None:
        """Aligned first, then nearby, shrinking the box when nothing fits."""
        for factor in SHRINK_STEPS:
            w = max(size[0] * factor, MIN_BOX_WIDTH)
            h = max(size[1] * factor, MIN_BOX_HEIGHT)
            aligned = self.place_aligned(anchors, directions, w, h)
            if aligned is not None:
                return aligned
            nearby = self.place_nearby(parent, w, h)
            if nearby is not None:
                return nearby, None
        return None

    def place_row(
        self, parent: Rect, count: int, directions: list[str], size: tuple[float, float]
    ) -> list[Rect] | None:
        """All boxes side by side under/over the parent, sharing its width."""
        if count < 2:
            return None
        width = (parent.width - (count - 1) * self.gap) / count
        if width < MIN_ROW_BOX_WIDTH:
            return None
        height = max(size[1] * 0.9, MIN_BOX_HEIGHT)
        for direction in directions:
            if direction not in ("below", "above"):
                continue
            y = (
                parent.bottom + self.gap
                if direction == "below"
                else parent.y - self.gap - height
            )
            row = [
                Rect(
                    round(parent.x + k * (width + self.gap), 2),
                    round(y, 2),
                    round(width, 2),
                    height,
                )
                for k in range(count)
            ]
            if all(
                fits(rect, self.occupied, self.page, self.clearance) for rect in row
            ):
                self.occupied.extend(row)
                return row
        return None

    def place_chain(
        self, parent: Rect, count: int, directions: list[str], size: tuple[float, float]
    ) -> list[Rect]:
        row = self.place_row(parent, count, directions, size)
        if row is not None:
            return row
        placed: list[Rect] = []
        last_direction: str | None = None
        for _ in range(count):
            anchors = [*reversed(placed), parent] if placed else [parent]
            order = directions
            if last_direction is not None:
                order = [
                    last_direction,
                    *[d for d in directions if d != last_direction],
                ]
            found = self.place_one(parent, anchors, order, size)
            if found is None:
                break
            placed.append(found[0])
            self.occupied.append(found[0])
            last_direction = found[1] or last_direction
        return placed


def _box_size(parent: Rect, scale: float) -> tuple[float, float]:
    return (
        max(parent.width * scale, MIN_BOX_WIDTH),
        max(parent.height * scale, MIN_BOX_HEIGHT),
    )


def _existing_indexes(scene: LayoutScene, input_key: str) -> int:
    indexes = {
        group.modifier_index
        for group in scene.groups
        if group.input_key == input_key and group.modifier_index is not None
    }
    return max(indexes, default=0)


@dataclass(frozen=True)
class PlanOptions:
    """Knobs shared by every input of one planning run."""

    arrangement: Arrangement = "auto"
    gap: float = DEFAULT_BOX_GAP
    scale: float = DEFAULT_BOX_SCALE
    max_count: int = DEFAULT_MAX_BOXES
    skip_existing: bool = True  # subtract the template's own KEY_MODIFIER_N boxes


@dataclass(frozen=True)
class GroupRequest:
    parent: SlotGroup
    parent_rect: Rect  # the parent's current bbox (after earlier ops)
    count: int
    start_index: int


def plan_boxes_for_group(
    planner: _Planner, request: GroupRequest, options: PlanOptions
) -> tuple[list[PlannedBox], list[Unplaced]]:
    parent, parent_rect, count = request.parent, request.parent_rect, request.count
    start_index = request.start_index
    directions = direction_order(
        parent_rect, options.arrangement, planner.occupied, planner.page
    )
    rects = planner.place_chain(
        parent_rect, count, directions, _box_size(parent_rect, options.scale)
    )
    placed = [
        PlannedBox(parent.target, start_index + k, rect, new_uid())
        for k, rect in enumerate(rects)
    ]
    unplaced = [
        Unplaced(parent.target, start_index + k, "no_space")
        for k in range(len(rects), count)
    ]
    return placed, unplaced


def plan_auto_add(
    scene: LayoutScene,
    counts: Mapping[str, int],
    options: PlanOptions | None = None,
    *,
    extra_occupied: Iterable[Rect] = (),
    parent_rects: Mapping[str, Rect] | None = None,
) -> AutoAddResult:
    """Plan boxes for ``counts`` (``input target → wanted boxes``), deterministically.

    ``options.skip_existing`` subtracts the template's own ``KEY_MODIFIER_N``
    boxes from the wanted count (the new boxes continue the numbering).
    ``parent_rects`` overrides a parent's bbox (its position after earlier
    layout ops); the op geometry is then relative to that rect.
    """
    options = options or PlanOptions()
    result = AutoAddResult()
    planner = _Planner(scene.page, scene.occupied(list(extra_occupied)), options.gap)
    for target in sorted(counts, key=natural_key):
        key, dup = parse_target(target)
        parent = scene.primary_for_input(key, dup)
        if parent is None or parent.bbox is None:
            result.unplaced.append(Unplaced(target, 0, "parent_missing"))
            continue
        if parent.background:
            result.unplaced.append(Unplaced(target, 0, "parent_background"))
            continue
        existing = _existing_indexes(scene, key) if options.skip_existing else 0
        needed = max(0, min(int(counts[target]), options.max_count) - existing)
        if needed == 0:
            continue
        parent_rect = (parent_rects or {}).get(parent.target, parent.bbox)
        request = GroupRequest(parent, parent_rect, needed, existing + 1)
        placed, unplaced = plan_boxes_for_group(planner, request, options)
        result.placed.extend(placed)
        result.unplaced.extend(unplaced)
        if placed:
            result.ops.append(_op_for(parent, parent_rect, placed, options))
    return result


def _op_for(
    parent: SlotGroup, parent_rect: Rect, placed: list[PlannedBox], options: PlanOptions
) -> AddModifierBoxesOp:
    boxes = [
        BoxGeometry(
            index=box.index,
            uid=box.uid,
            dx=round(box.rect.x - parent_rect.x, 2),
            dy=round(box.rect.y - parent_rect.y, 2),
            width=round(box.rect.width, 2),
            height=round(box.rect.height, 2),
        )
        for box in placed
    ]
    return AddModifierBoxesOp(
        target=parent.target,
        count=len(boxes),
        max_count=options.max_count,
        arrangement=options.arrangement,
        gap=options.gap,
        scale=options.scale,
        boxes=boxes,
    )


# ── Convenience ──


def counts_from_device(device, max_count: int = DEFAULT_MAX_BOXES) -> dict[str, int]:
    """``input key → min(bound modifiers, max_count)`` for every input with modifiers."""
    counts: dict[str, int] = {}
    for key, input_obj in device.get_combined_inputs().items():
        bound = len(input_obj.modifiers)
        if bound:
            counts[key.lower()] = min(bound, max_count)
    return counts


def auto_add_for_template(
    raw_svg: str, counts: Mapping[str, int], options: PlanOptions | None = None
) -> AutoAddResult:
    """Parse a template, build its scene and plan boxes (see ``plan_auto_add``)."""
    from joystick_diagrams.render.adapters import detect_adapter
    from joystick_diagrams.render.document import TemplateDocument
    from joystick_diagrams.render.drawio_model import DrawioModel
    from joystick_diagrams.render.layout_scene import build_scene

    doc = TemplateDocument.parse(raw_svg)
    model = DrawioModel.from_content(doc.root.get("content"))
    slot_map = detect_adapter(doc, model).build_slots(doc, model)
    scene = build_scene(slot_map, doc.root, model)
    return plan_auto_add(scene, counts, options)


__all__ = [
    "DIRECTIONS",
    "AutoAddResult",
    "GroupRequest",
    "PlanOptions",
    "PlannedBox",
    "Unplaced",
    "auto_add_for_template",
    "counts_from_device",
    "direction_order",
    "fits",
    "natural_key",
    "plan_auto_add",
]

if __name__ == "__main__":
    pass
