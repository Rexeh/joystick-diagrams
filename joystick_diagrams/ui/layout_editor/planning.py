"""Box placement helpers for the Layout screen (Qt-free).

Wraps ``render/auto_layout.plan_auto_add`` with what the screen knows: the
pristine template (parsed once per template and cached) and the last
``EditorRender`` (slot positions after the stored ops, and the boxes already
added), so new boxes avoid everything that is on the diagram right now.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from joystick_diagrams.render.auto_layout import (
    AutoAddResult,
    PlanOptions,
    counts_from_device,
    plan_auto_add,
)
from joystick_diagrams.render.layout import DEFAULT_MAX_BOXES, parse_target
from joystick_diagrams.render.layout_scene import LayoutScene, build_scene
from joystick_diagrams.render.slots import Rect

MODIFIER_ROLES = frozenset({"modifier", "modifier_key", "modifier_action"})
ARRANGEMENT_ORDER = ("auto", "below", "right", "left", "above")


class SceneCache:
    """``LayoutScene`` per template key (the template never changes while open)."""

    def __init__(self) -> None:
        self._scenes: dict[str, LayoutScene] = {}

    def scene_for(self, template: Any) -> LayoutScene:
        key = getattr(template, "template_key", None) or id(template)
        scene = self._scenes.get(key)
        if scene is None:
            scene = build_scene_for(template.raw_data)
            self._scenes[key] = scene
        return scene

    def clear(self) -> None:
        self._scenes.clear()


def build_scene_for(raw_svg: str) -> LayoutScene:
    from joystick_diagrams.render.adapters import detect_adapter
    from joystick_diagrams.render.document import TemplateDocument
    from joystick_diagrams.render.drawio_model import DrawioModel

    doc = TemplateDocument.parse(raw_svg)
    model = DrawioModel.from_content(doc.root.get("content"))
    slot_map = detect_adapter(doc, model).build_slots(doc, model)
    return build_scene(slot_map, doc.root, model)


@dataclass(frozen=True)
class RenderGeometry:
    """What the last render says about where things are now."""

    parent_rects: dict[str, Rect]
    added_rects: list[Rect]
    added_boxes: dict[str, list[int]]  # input key → modifier indexes added by ops


def geometry_from_render(render: Any) -> RenderGeometry:
    parents: dict[str, Rect] = {}
    added: list[Rect] = []
    boxes: dict[str, list[int]] = {}
    for slot in getattr(render, "slots", ()) or ():
        if slot.bbox is None:
            continue
        if slot.added_uid:
            added.append(slot.bbox)
            if slot.input_key and slot.modifier_index:
                boxes.setdefault(slot.input_key, []).append(slot.modifier_index)
        elif not slot.hidden:
            parents[slot.target] = slot.bbox
    return RenderGeometry(parents, added, boxes)


def template_box_indexes(render: Any, input_key: str) -> list[int]:
    """Modifier box indexes the template itself has for ``input_key``."""
    return sorted(
        {
            slot.modifier_index
            for slot in getattr(render, "slots", ()) or ()
            if not slot.added_uid
            and slot.input_key == input_key
            and slot.role in MODIFIER_ROLES
            and slot.modifier_index
        }
    )


def box_count(render: Any, input_key: str) -> int:
    """Boxes (template + added) available to ``input_key`` on this render."""
    geometry = geometry_from_render(render)
    indexes = set(template_box_indexes(render, input_key))
    indexes.update(geometry.added_boxes.get(input_key, []))
    return len(indexes)


def next_box_index(render: Any, input_key: str) -> int:
    geometry = geometry_from_render(render)
    used = set(template_box_indexes(render, input_key))
    used.update(geometry.added_boxes.get(input_key, []))
    return max(used, default=0) + 1


def plan_for_render(
    scene: LayoutScene,
    render: Any,
    counts: Mapping[str, int],
    options: PlanOptions | None = None,
) -> AutoAddResult:
    """Plan boxes around the slots' *current* positions, avoiding added boxes.

    ``counts`` is the total number of boxes each input should end up with
    (``counts_from_device`` style). Boxes the template has and boxes already
    added by earlier ops are subtracted, and the new boxes continue the
    numbering after them.
    """
    options = options or PlanOptions()
    geometry = geometry_from_render(render)
    needed: dict[str, int] = {}
    offsets: dict[str, int] = {}
    for key, requested in counts.items():
        wanted = min(int(requested), options.max_count)
        have = box_count(render, key)
        if wanted > have:
            needed[key] = wanted - have
            offsets[key] = next_box_index(render, key) - 1
    plain = PlanOptions(
        arrangement=options.arrangement,
        gap=options.gap,
        scale=options.scale,
        max_count=options.max_count,
        skip_existing=False,
    )
    result = plan_auto_add(
        scene,
        needed,
        plain,
        extra_occupied=geometry.added_rects,
        parent_rects=geometry.parent_rects,
    )
    # Continue the numbering after the boxes that already exist.
    result.ops = [
        op.model_copy(
            update={
                "boxes": [
                    box.model_copy(
                        update={
                            "index": box.index + offsets.get(op.target.split("#")[0], 0)
                        }
                    )
                    for box in (op.boxes or [])
                ]
            }
        )
        for op in result.ops
    ]
    result.placed = [
        box.__class__(
            box.target,
            box.index + offsets.get(box.target.split("#")[0], 0),
            box.rect,
            box.uid,
        )
        for box in result.placed
    ]
    return result


def plan_one_box(
    scene: LayoutScene, render: Any, target: str, arrangement: str = "auto"
) -> Rect | None:
    """Where one more box for ``target`` fits (relative geometry is up to the caller)."""
    key, _dup = parse_target(target)
    options = PlanOptions(arrangement=arrangement, skip_existing=False, max_count=99)
    geometry = geometry_from_render(render)
    occupied = list(geometry.added_rects)
    result = plan_auto_add(
        scene,
        {target: 1},
        options,
        extra_occupied=occupied,
        parent_rects=geometry.parent_rects,
    )
    if not result.placed:
        return None
    return result.placed[0].rect


def counts_for_devices(
    devices: Iterable[Any], max_count: int = DEFAULT_MAX_BOXES
) -> dict[str, int]:
    """Per input, the most modifiers any of ``devices`` binds (capped)."""
    counts: dict[str, int] = {}
    for device in devices:
        for key, count in counts_from_device(device, max_count).items():
            counts[key] = max(counts.get(key, 0), count)
    return counts


def needed_counts(render: Any, counts: Mapping[str, int]) -> dict[str, int]:
    """Inputs that still need boxes: ``counts`` minus the boxes already there."""
    needed: dict[str, int] = {}
    for key, wanted in counts.items():
        have = box_count(render, key)
        if wanted > have:
            needed[key] = wanted
    return needed


__all__ = [
    "ARRANGEMENT_ORDER",
    "MODIFIER_ROLES",
    "RenderGeometry",
    "SceneCache",
    "box_count",
    "build_scene_for",
    "counts_for_devices",
    "geometry_from_render",
    "needed_counts",
    "next_box_index",
    "plan_for_render",
    "plan_one_box",
    "template_box_indexes",
]

if __name__ == "__main__":
    pass
