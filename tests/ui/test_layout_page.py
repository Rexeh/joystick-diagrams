"""Customise → Layout page logic without QtWebEngine (the canvas is never shown).

Rendering runs synchronously through ``render_synchronously`` so the panel,
notices, gestures and persistence can be checked on the offscreen platform.
"""

import json
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.db.layout_service import LayoutService  # noqa: E402
from joystick_diagrams.render.layout import TEMPLATE_LAYER, MoveOp  # noqa: E402
from joystick_diagrams.ui import strings_layout as S  # noqa: E402
from joystick_diagrams.ui.customise_layout import CustomiseLayout  # noqa: E402
from tests.ui.layout_fixtures import (  # noqa: E402
    DEVICE_GUID,
    DEVICE_NAME,
    STARTER_TEMPLATE,
    seed_layout_state,
)

STARTER_KEY = "bundled:Starter Template.svg"


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


@pytest.fixture
def settings_store():
    values: dict[str, str] = {}
    with (
        patch("joystick_diagrams.db.db_settings.get_setting", side_effect=values.get),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value",
            side_effect=values.__setitem__,
        ),
    ):
        yield values


@pytest.fixture
def page(settings_store):
    seed_layout_state()
    page = CustomiseLayout()
    page.refresh()
    page.render_synchronously()
    yield page
    page.shutdown()


def stored(layer=TEMPLATE_LAYER):
    return LayoutService().get_document(STARTER_KEY, layer).ops


@pytest.mark.uitest
def test_empty_state_without_templates(qapp, settings_store):
    seed_layout_state(assign_template=False)
    page = CustomiseLayout()
    page.refresh()
    assert page.canvas_stack.currentWidget() is page.empty_state
    assert not page.add_box_button.isEnabled()
    assert page.render_synchronously() is None
    assert page._canvas is None  # WebEngine never started


@pytest.mark.uitest
def test_header_lists_diagram_profiles_and_scope(qapp, page, settings_store):
    assert page.diagram_combo.count() == 1
    assert page.diagram_combo.currentText().startswith(DEVICE_NAME)
    assert page.diagram_combo.currentData() == DEVICE_GUID
    assert [page.profile_combo.itemText(i) for i in range(2)] == [
        "DCS World / F-16C",
        "DCS World / Mirage",
    ]
    assert page.scope_profile.text() == "Only F-16C"
    assert page.scope_all.isChecked() and page.scope_layer == TEMPLATE_LAYER
    assert page._render is not None and page._render.supported
    assert not page.banner.isVisibleTo(page)
    assert page.panel_empty.isVisibleTo(page)
    assert page._canvas is None


@pytest.mark.uitest
def test_gesture_from_the_canvas_persists_a_move_and_undo_redo(qapp, page):
    page.bridge.applyGesture(
        json.dumps({"gesture": "move", "target": "button_1#1", "dx": 20, "dy": 5})
    )
    ops = stored()
    assert len(ops) == 1 and isinstance(ops[0], MoveOp) and ops[0].dx == 20
    assert page.undo_button.isEnabled() and not page.redo_button.isEnabled()
    render = page.render_synchronously()
    slot = next(s for s in render.slots if s.target == "button_1#1")
    assert (slot.dx, slot.dy) == (20, 5) and slot.layer == "template"

    page.undo()
    assert stored() == [] and page.redo_button.isEnabled()
    page.redo()
    assert len(stored()) == 1

    # Nudges coalesce; a resize with a top-left shift is one step
    page.bridge.nudge("button_1#1", 1, 0)
    page.bridge.nudge("button_1#1", 0, 1)
    assert len(stored()) == 2
    page.bridge.applyGesture(
        json.dumps(
            {
                "gesture": "resize",
                "target": "button_2#1",
                "dx": -5,
                "dy": 0,
                "width": 150,
                "height": 44,
            }
        )
    )
    assert [op.op for op in stored()][-2:] == ["move", "resize"]
    page.undo()
    assert len(stored()) == 2


@pytest.mark.uitest
def test_scope_switch_writes_to_the_profile_layer(qapp, page, settings_store):
    page.scope_profile.setChecked(True)
    assert page.scope_layer == "dcs world_f-16c"
    assert settings_store["layout_editor_last_scope"] == "profile"
    page.bridge.applyGesture(
        json.dumps({"gesture": "move", "target": "button_3#1", "dx": 1, "dy": 1})
    )
    assert stored() == [] and len(stored("dcs world_f-16c")) == 1
    render = page.render_synchronously()
    slot = next(s for s in render.slots if s.target == "button_3#1")
    assert slot.layer == "profile"
    page._on_selection_changed("button_3#1")
    assert page.selection_profile.isVisibleTo(page)
    assert page.selection_profile.text() == "Changed only for F-16C"

    # Switching the previewed profile hides that change (other layer) and keeps scope
    page.profile_combo.setCurrentIndex(1)
    assert page.scope_profile.text() == "Only Mirage"
    assert page.scope_layer == "dcs world_mirage"
    render = page.render_synchronously()
    slot = next(s for s in render.slots if s.target == "button_3#1")
    assert slot.layer is None and slot.dx == 0


@pytest.mark.uitest
def test_panel_shows_selection_geometry_and_edits_through_spin_boxes(qapp, page):
    page._on_selection_changed("button_1#1")
    assert page.panel_selection.isVisibleTo(page)
    assert page.selection_title.text() == "Button 1"
    assert page.selection_origin.text() == "Button 1 · from the template"
    assert page.modifier_count_label.text() == S.PANEL_MODIFIER_BOXES.format(count=1)
    assert page.spin_w.isEnabled() and page.spin_x.isEnabled()
    before = page.spin_x.value()
    page.spin_x.setValue(before + 15)
    page._on_position_edited()
    assert stored()[-1].dx == 15
    page.spin_w.setValue(200)
    page._on_size_edited()
    assert stored()[-1].op == "resize" and stored()[-1].width == 200
    page.render_synchronously()
    assert page.spin_x.value() == before + 15 and page.spin_w.value() == 200


@pytest.mark.uitest
def test_add_box_hide_and_undo_changes_to_a_box(qapp, page):
    page._on_selection_changed("button_1#1")
    page.add_modifier_box()
    ops = stored()
    assert ops[-1].op == "add_modifier_box" and ops[-1].index == 2
    render = page.render_synchronously()
    added = [s for s in render.slots if s.added_uid]
    assert len(added) == 1 and added[0].parent == "button_1#1"
    assert page._selected == added[0].target  # the new box is selected
    assert page.panel_hide.text() == S.PANEL_REMOVE_BOX
    assert page.modifier_count_label.text() == S.PANEL_MODIFIER_BOXES.format(count=2)

    page.hide_selected()  # removes the added box
    assert stored()[-1].op == "remove_added"
    page.render_synchronously()
    page._on_selection_changed("button_4#1")
    page.hide_selected()
    assert stored()[-1].op == "hide" and stored()[-1].target == "button_4#1"
    render = page.render_synchronously()
    assert next(s for s in render.slots if s.target == "button_4#1").hidden
    assert page.panel_hide.text() == S.PANEL_SHOW_BOX
    page.undo_changes_to_selected()
    assert all(op.target != "button_4#1" for op in stored())


@pytest.mark.uitest
def test_notices_report_overflow_and_template_updates(qapp, page):
    notices = page.build_notices()
    texts = [n.text for n in notices]
    # F-16C: Pickle has 3 modifiers, the Starter template gives BUTTON_1 one box
    assert any(t.startswith("Pickle has 2 more modifiers than boxes.") for t in texts)
    assert any("don't appear" in t for t in texts)
    assert notices[0].action_text == S.NOTICE_OVERFLOW_ACTION

    # Ops saved against other template bytes, one of them no longer fits
    service = page.service
    service.set_ops(
        STARTER_KEY, TEMPLATE_LAYER, [MoveOp(target="button_99", dx=1, dy=1)], "old"
    )
    page.render_synchronously()
    texts = [n.text for n in page.build_notices()]
    assert any(
        "This template was updated on" in t and "1 of your changes no longer fit" in t
        for t in texts
    )


@pytest.mark.uitest
def test_reset_all_and_show_device(qapp, page):
    page.bridge.applyGesture(
        json.dumps({"gesture": "move", "target": "button_1#1", "dx": 2, "dy": 2})
    )
    with patch(
        "joystick_diagrams.ui.customise_layout.QMessageBox.question",
        return_value=16384,  # QMessageBox.StandardButton.Yes
    ):
        page.reset_all()
    assert page.service.layers_of_template(STARTER_KEY) == []
    page.undo()
    assert len(stored()) == 1
    page.show_device(DEVICE_GUID)
    assert page.diagram_combo.currentData() == DEVICE_GUID


@pytest.mark.uitest
def test_configure_page_has_layout_nav_and_navigation(qapp, settings_store):
    from joystick_diagrams.ui.configure_page import configurePage

    seed_layout_state()
    page = configurePage()
    labels = [page.nav_list.item(i).text() for i in range(page.nav_list.count())]
    assert labels[-1] == S.NAV_LAYOUT
    page.show_layout(DEVICE_GUID)
    assert page.stack.currentWidget() is page.layout_screen
    assert page.layout_screen.diagram_combo.currentData() == DEVICE_GUID
    page.shutdown()
    assert STARTER_TEMPLATE.exists()
