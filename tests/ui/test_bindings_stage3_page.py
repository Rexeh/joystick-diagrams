"""3. Bindings: controller picker, profile filter, labels, Shared bindings link."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402

from joystick_diagrams.ui import strings_bindings as S  # noqa: E402
from joystick_diagrams.ui.bindings_page import BindingsPage  # noqa: E402
from joystick_diagrams.ui.customise_labels import CustomiseLabels  # noqa: E402
from joystick_diagrams.ui.customise_profiles import (  # noqa: E402
    CHIPS_ROLE,
    COLUMN_ACTION,
    COLUMN_MODIFIER,
    INHERITED_FROM_ROLE,
)
from joystick_diagrams.ui.stage_contract import STAGE_DIAGRAMS  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    PANEL,
    STICK,
    THROTTLE,
    _reset_app_state,
    make_wrapper,
    seed_state,
    settings_store,
)


@pytest.fixture
def page(qapp, settings_store):
    seed_state()
    page = BindingsPage()
    page.refresh()
    return page


def combo_items(combo):
    return [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]


@pytest.mark.uitest
def test_controller_picker_lists_ready_controllers_and_all(page):
    screen = page.profiles_screen
    items = combo_items(screen.controller_combo)
    # Ready controllers by name, then "All controllers (by profile)"; the panel
    # without a template is not offered.
    assert [d for _t, d in items] == [STICK, THROTTLE, ""]
    assert items[-1][0] == S.ALL_CONTROLLERS
    assert PANEL not in [d for _t, d in items]


@pytest.mark.uitest
def test_profile_picker_is_filtered_to_the_controller(page):
    screen = page.profiles_screen
    screen.select_controller(THROTTLE)
    texts = [t for t, _d in combo_items(screen.profile_combo)]
    assert texts == [
        "DCS World / F-16C (2 bindings)",
        "DCS World / Common (1 binding)",
    ]
    screen.select_controller(STICK)
    texts = [t for t, _d in combo_items(screen.profile_combo)]
    assert texts == [
        "DCS World / F-16C (4 bindings)",
        "DCS World / A-10C (1 binding)",
    ]
    tree = screen.viewBindsTreeWidget
    assert [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())] == [
        "Button 1",
        "Button 2",
        "Button 99",
    ]
    modifier = tree.topLevelItem(0).child(0)
    assert modifier.text(COLUMN_ACTION) == "Pickle (LShift)"
    chips = modifier.data(COLUMN_MODIFIER, CHIPS_ROLE)
    assert chips == [("LShift", "#0072B2")]  # Shift group colour


@pytest.mark.uitest
def test_all_controllers_is_the_profile_first_tree(page):
    screen = page.profiles_screen
    screen.select_controller("")
    screen.select_profile("dcs world_f-16c")
    tree = screen.viewBindsTreeWidget
    roots = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert roots == ["Button Box", "Gladiator NXT", "Warthog Throttle"]


@pytest.mark.uitest
def test_edit_label_updates_every_row_and_the_hint(page):
    screen = page.profiles_screen
    screen.select_controller(STICK)
    assert screen.hint_label.text() == S.RELABEL_HINT
    tree = screen.viewBindsTreeWidget
    tree.setCurrentItem(tree.topLevelItem(1))
    assert screen.edit_label_button.isEnabled()
    screen.set_label("Trigger", "Trig")
    assert tree.topLevelItem(1).text(COLUMN_ACTION) == 'Trigger   shown as "Trig"'
    assert page.appState.label_service.resolve("Trigger") == "Trig"
    screen.set_label("Trigger", "Trigger")  # the game's text removes the label
    assert not page.appState.label_service.has_custom_label("Trigger")


@pytest.mark.uitest
def test_f2_opens_the_label_editor(page, qtbot):
    screen = page.profiles_screen
    screen.select_controller(STICK)
    tree = screen.viewBindsTreeWidget
    tree.setCurrentItem(tree.topLevelItem(0))
    page.show()
    qtbot.keyClick(tree, Qt.Key.Key_F2)
    assert tree.state() == tree.State.EditingState
    assert tree.currentColumn() == COLUMN_ACTION


@pytest.mark.uitest
def test_inherited_binding_shows_its_source_and_opens_shared(qapp, settings_store):
    state = seed_state()
    child, common = state.profile_wrappers[0], state.profile_wrappers[2]
    # F-16C uses bindings from Common: Button 3 on the throttle comes from there
    merged = make_wrapper(
        "F-16C", {THROTTLE: {1: ("Speed brake", []), 3: ("Comms", [])}}
    )
    child.profile = merged.profile
    child.parents = [common]
    page = BindingsPage()
    page.refresh()
    screen = page.profiles_screen
    screen.select_controller(THROTTLE)
    screen.select_profile(child.profile_key)
    tree = screen.viewBindsTreeWidget
    row = next(
        tree.topLevelItem(i)
        for i in range(tree.topLevelItemCount())
        if tree.topLevelItem(i).text(0) == "Button 3"
    )
    assert row.data(COLUMN_ACTION, INHERITED_FROM_ROLE)[1] == "DCS World / Common"
    assert '(from "DCS World / Common")' in row.text(COLUMN_ACTION)
    tree.setCurrentItem(row)
    assert screen.source_row.isVisibleTo(screen)
    screen.open_shared_button.click()
    assert page.current_section() == "shared"


@pytest.mark.uitest
def test_labels_filter_only_used_on_controller(page):
    labels = page.appState.label_service
    labels.set_label("Pickle", "Bombs")
    labels.set_label("Speed brake", "SB")
    page.show_section("labels")
    screen = page.labels_screen
    assert screen.table.rowCount() == 2
    screen.set_filter_device(STICK)
    assert screen.table.rowCount() == 1
    assert screen.table.item(0, 0).text() == "Pickle"
    screen.set_filter_device(THROTTLE)
    assert screen.table.item(0, 0).text() == "Speed brake"


@pytest.mark.uitest
def test_labels_layout_does_not_move_when_empty(qapp, settings_store):
    seed_state()
    from joystick_diagrams.app_state import AppState

    def help_y() -> tuple[int, int]:
        screen = CustomiseLabels()
        screen.resize(900, 970)
        screen.refresh()
        screen.show()
        qapp.processEvents()
        help_label = screen.findChild(type(screen._empty_label), "device_help_label")
        result = (
            help_label.y(),
            screen.filter_combo.parentWidget()
            .mapTo(screen, screen.filter_combo.pos())
            .y(),
        )
        screen.close()
        return result

    empty = help_y()
    AppState().label_service.set_label("Pickle", "Bombs")
    one = help_y()
    assert empty == one


@pytest.mark.uitest
def test_shared_bindings_hosts_the_clash_rule(page, settings_store):
    page.show_section("shared")
    screen = page.inheritance_screen
    assert screen.clash_combo.count() == 3
    assert screen.clash_combo.itemText(0) == S.CLASH_KEEP


@pytest.mark.uitest
def test_stage_status_and_next_action(page):
    status = page.stage_status()
    assert (status.icon, status.text) == ("none", "Optional · 3 profiles")
    action = page.next_action()
    assert action.label == "Next: 4. Diagrams ›"
    seen = []
    page.request_stage.connect(lambda index, payload: seen.append((index, payload)))
    action.callback()
    assert seen == [(STAGE_DIAGRAMS, {})]


@pytest.mark.uitest
def test_deep_link_selects_the_controller(page):
    page.navigate({"device_guid": THROTTLE})
    assert page.current_section() == "bindings"
    assert page.profiles_screen.current_controller() == THROTTLE
