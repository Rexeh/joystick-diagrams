"""Automatic modifier-box placement: determinism, no overlap, page bounds, reasons."""

import pytest

from joystick_diagrams.render.adapters import detect_adapter
from joystick_diagrams.render.auto_layout import (
    PlanOptions,
    auto_add_for_template,
    counts_from_device,
    direction_order,
    natural_key,
    plan_auto_add,
)
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.layout_scene import build_scene
from joystick_diagrams.render.slots import Rect
from tests.render.render_fixtures import (
    CellSpec,
    DrawioFixture,
    basic_fixture,
    build_svg,
)


def scene_for(fx):
    doc = TemplateDocument.parse(build_svg(fx))
    model = DrawioModel.from_content(doc.root.get("content"))
    slot_map = detect_adapter(doc, model).build_slots(doc, model)
    return build_scene(slot_map, doc.root, model)


def test_natural_key_orders_button_10_after_button_2():
    keys = sorted(["button_10", "button_2", "axis_x", "button_1"], key=natural_key)
    assert keys == ["axis_x", "button_1", "button_2", "button_10"]


def test_plan_is_deterministic_without_overlaps_and_inside_page():
    scene = scene_for(basic_fixture())
    counts = {"button_1": 3, "button_2": 2, "axis_x": 1, "pov_1_u": 2}
    first = plan_auto_add(scene, counts)
    second = plan_auto_add(scene_for(basic_fixture()), counts)
    assert [(b.target, b.index, b.rect) for b in first.placed] == [
        (b.target, b.index, b.rect) for b in second.placed
    ]
    assert first.overlaps(scene.occupied()) == 0
    assert all(scene.page.contains(b.rect) for b in first.placed)
    assert first.unplaced == []
    # button_1 already has a MODIFIER_1 box: only indexes 2 and 3 are added.
    assert [b.index for b in first.placed if b.target == "button_1#1"] == [2, 3]
    op = next(op for op in first.ops if op.target == "button_1#1")
    assert op.count == 2 and [b.index for b in op.boxes] == [2, 3]
    first_box = next(b for b in first.placed if b.target == "button_1#1")
    assert op.boxes[0].dx == first_box.rect.x - scene.group("button_1#1").bbox.x


def test_unplaced_reasons_and_shrinking():
    fx = DrawioFixture(
        width=120, height=90, cells=[CellSpec("a", "BUTTON_1", 10, 10, 90, 30)]
    )
    scene = scene_for(fx)
    result = plan_auto_add(scene, {"button_1": 4, "button_9": 1})
    reasons = {(u.target, u.reason) for u in result.unplaced}
    assert ("button_9", "parent_missing") in reasons
    assert ("button_1#1", "no_space") in reasons
    assert result.placed  # at least one (shrunk) box fits under the slot
    assert all(b.rect.width >= 28 and b.rect.height >= 11 for b in result.placed)


def test_background_parent_is_refused():
    fx = DrawioFixture(
        width=200, height=100, cells=[CellSpec("bg", "BUTTON_22", 0, 0, 190, 90)]
    )
    result = plan_auto_add(scene_for(fx), {"button_22": 1})
    assert [u.reason for u in result.unplaced] == ["parent_background"]


def test_direction_preference_and_auto_ranking():
    page = Rect(0, 0, 400, 300)
    parent = Rect(100, 100, 80, 30)
    blocker = Rect(100, 135, 80, 30)  # right under the parent
    assert direction_order(parent, "below", [blocker], page)[0] == "below"
    auto = direction_order(parent, "auto", [blocker], page)
    assert auto[-1] == "below" and auto[0] == "right"


def test_parent_rect_override_and_extra_occupied():
    scene = scene_for(basic_fixture())
    moved = Rect(300, 60, 80, 30)
    result = plan_auto_add(
        scene,
        {"button_2": 1},
        PlanOptions(arrangement="below"),
        parent_rects={"button_2#1": moved},
    )
    (box,) = result.placed
    assert box.rect.y == moved.bottom + 5 and box.rect.x == moved.x
    blocked = plan_auto_add(
        scene,
        {"button_2": 1},
        PlanOptions(arrangement="below"),
        parent_rects={"button_2#1": moved},
        extra_occupied=[Rect(295, 90, 90, 40)],
    )
    assert blocked.placed[0].rect != box.rect


def test_counts_from_device_and_template_helper():
    from joystick_diagrams.input.button import Button
    from tests.render.render_fixtures import new_device

    dev = new_device()
    dev.create_input(Button(1), "Fire")
    for key in ("a", "b", "c", "d", "e"):
        dev.add_modifier_to_input(Button(1), {key}, key)
    dev.create_input(Button(2), "No modifiers")
    assert counts_from_device(dev, max_count=4) == {"button_1": 4}
    result = auto_add_for_template(build_svg(basic_fixture()), {"button_1": 2})
    assert [b.index for b in result.placed] == [2]


@pytest.mark.parametrize("arrangement", ["below", "right", "left", "above"])
def test_every_arrangement_places_without_overlap(arrangement):
    scene = scene_for(basic_fixture())
    result = plan_auto_add(
        scene, {"button_2": 2, "pov_1_u": 2}, PlanOptions(arrangement=arrangement)
    )
    assert result.overlaps(scene.occupied()) == 0
