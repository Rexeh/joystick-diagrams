"""2. Controllers: empty state, grouping from device_status, the make-diagram
toggle, footer actions and deep links."""

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from joystick_diagrams.ui.controllers_page import (  # noqa: E402
    GROUP_NEEDS,
    GROUP_NO_DIAGRAM,
    GROUP_READY,
    ControllersPage,
    compute_statuses,
)
from joystick_diagrams.ui.stage_shell import mark_first_run_done  # noqa: E402
from tests.ui.stage_fixtures import (  # noqa: E402
    KEYBOARD,
    STICK,
    TEST_TEMPLATE,
    THROTTLE,
    VJOY,
    FakeProfileWrapper,
    drain,
    patched_settings,
    profile_with,
    seed_app_state,
)


@pytest.fixture(autouse=True)
def _fresh_state(temp_database):
    with patched_settings():
        seed_app_state()
        yield
    drain()
    from joystick_diagrams.app_state import AppState

    AppState._inst = None


def make_page(qtbot, profiles=None, throttle_template=True):
    state = seed_app_state(profile_wrappers=profiles)
    if throttle_template:
        state.device_service.set_template(THROTTLE, TEST_TEMPLATE)
    page = ControllersPage()
    qtbot.addWidget(page)
    return page, state


def read_profiles():
    return [
        FakeProfileWrapper(profile_with("F-16C"), game="Joystick Gremlin"),
        FakeProfileWrapper(profile_with("A-10C"), game="Joystick Gremlin"),
    ]


def test_empty_state_before_any_read(qtbot):
    page, _ = make_page(qtbot, profiles=[], throttle_template=False)
    assert page.stack.currentIndex() == 0
    assert page.empty_state.message_label.text() == (
        "Your controllers appear here once we've read a game."
    )
    assert page.stage_status().text == "Found when a game is read"
    assert page.next_action() is None
    with qtbot.waitSignal(page.request_stage) as blocker:
        page.empty_state.action_button.click()
    assert blocker.args == [0, {}]


def test_groups_come_from_device_status(qtbot):
    page, _ = make_page(qtbot, read_profiles())
    assert page.stack.currentIndex() == 1
    # A keyboard with bindings is a controller like any other: no name guessing
    assert set(page.group_guids(GROUP_NEEDS)) == {STICK, KEYBOARD}
    assert page.group_guids(GROUP_READY) == [THROTTLE]
    assert page.group_guids(GROUP_NO_DIAGRAM) == [VJOY]
    assert page.is_group_expanded(GROUP_NEEDS)
    assert not page.is_group_expanded(GROUP_NO_DIAGRAM)  # collapsed by default
    assert page.row_text(STICK) == "No template · 2 profiles"
    assert page.row_text(THROTTLE) == "template_test · 2 profiles"
    assert page.row_text(KEYBOARD) == "No template · 2 profiles"
    assert page.row_text(VJOY) == "Nothing bound"
    status = page.stage_status()
    assert status.icon == "warning" and status.text == "2 need a template"


def test_summary_matches_the_page(qtbot):
    page, _ = make_page(qtbot, read_profiles())
    summary = compute_statuses()
    assert set(summary.needs) == set(page.summary.needs) == {STICK, KEYBOARD}
    assert summary.diagram_count == 2  # the throttle in two profiles


def test_template_section_first_and_buttons(qtbot):
    page, _ = make_page(qtbot, read_profiles())
    page.select_guid(STICK)
    assert page.selected_guid == STICK
    assert page.template_name.text() == (
        "No template yet. Choose the one that matches this controller."
    )
    assert page.choose_button.text() == "Choose template…"
    assert page.preview_button.isHidden()
    page.select_guid(THROTTLE)
    assert page.choose_button.text() == "Change template…"
    assert page.template_name.text() == "template_test"
    assert page.template_source.text() == "data"  # a file outside the catalogue
    assert not page.edit_layout_button.isHidden()
    assert page.used_in.text() == "Used in: Joystick Gremlin · 2 profiles"


def test_make_diagram_toggle_is_the_one_user_control(qtbot):
    page, state = make_page(qtbot, read_profiles())
    page.select_guid(STICK)
    assert page.make_diagram.isChecked()
    page.make_diagram.setChecked(False)
    kind = state.device_service.kind(STICK)
    assert kind.is_user and kind.no_diagram
    assert STICK in page.group_guids(GROUP_NO_DIAGRAM)
    assert page.row_text(STICK) == "Set by you"
    page.select_guid(STICK)
    assert page.reason_label.text() == "· Set by you"
    page.make_diagram.setChecked(True)
    assert STICK in page.group_guids(GROUP_NEEDS)


def test_automatic_no_diagram_shows_its_reason_and_can_be_overridden(qtbot):
    page, state = make_page(qtbot, read_profiles())
    page.select_guid(VJOY)
    assert not page.make_diagram.isChecked()
    assert page.reason_label.text() == "· Nothing bound"
    page.make_diagram.setChecked(True)
    assert VJOY in page.group_guids(GROUP_NEEDS)


def test_next_action_first_run_then_guidance(qtbot):
    page, state = make_page(qtbot, read_profiles())
    # The keyboard is a controller until the user says otherwise
    state.device_service.set_make_diagram(KEYBOARD, False)
    page.refresh()
    # Templates to choose: choosing is the primary, the way on is the quieter one
    assert page.next_action().label == "Choose 1 template"
    assert page.secondary_action().label == "Next: 3. Bindings ›"
    with patch.object(page, "choose_template_for") as choose:
        page.next_action().callback()
    choose.assert_called_once_with(STICK)
    mark_first_run_done()
    action = page.next_action()
    assert action.label == "Choose 1 template"
    state.device_service.set_template(STICK, TEST_TEMPLATE)
    page.refresh()
    assert page.stage_status().text == "All 2 ready"
    assert page.secondary_action() is None
    action = page.next_action()
    assert action.label == "Next: 4. Diagrams ›"
    with qtbot.waitSignal(page.request_stage) as blocker:
        action.callback()
    assert blocker.args == [3, {}]


def test_nothing_ready_footer_is_choose_n_plus_skip(qtbot):
    page, state = make_page(qtbot, read_profiles(), throttle_template=False)
    state.device_service.set_make_diagram(KEYBOARD, False)
    page.refresh()
    action = page.next_action()
    assert action.label == "Choose 2 templates"
    skip = page.secondary_action()
    assert skip.label == "Skip to 3. Bindings ›"
    with qtbot.waitSignal(page.request_stage) as blocker:
        skip.callback()
    assert blocker.args == [2, {}]


def test_first_run_with_everything_ready_goes_to_bindings(qtbot):
    page, state = make_page(qtbot, read_profiles())
    state.device_service.set_make_diagram(KEYBOARD, False)
    state.device_service.set_template(STICK, TEST_TEMPLATE)
    page.refresh()
    assert page.next_action().label == "Next: 3. Bindings ›"


def test_deep_links(qtbot):
    page, _ = make_page(qtbot, read_profiles())
    page.select_guid(THROTTLE)
    with qtbot.waitSignal(page.request_stage) as blocker:
        page.edit_layout_button.click()
    assert blocker.args == [3, {"device_guid": THROTTLE, "section": "layout"}]
    with qtbot.waitSignal(page.request_stage) as blocker:
        page.view_bindings_button.click()
    assert blocker.args == [2, {"device_guid": THROTTLE}]


def test_handle_request_selects_the_controller(qtbot):
    page, _ = make_page(qtbot, read_profiles())
    page.handle_request({"device_guid": VJOY})
    assert page.selected_guid == VJOY
    assert page.is_group_expanded(GROUP_NO_DIAGRAM)


def test_refresh_keeps_the_selection(qtbot):
    page, _ = make_page(qtbot, read_profiles())
    page.select_guid(THROTTLE)
    page.refresh()
    assert page.selected_guid == THROTTLE


def test_snapshot_before_this_sessions_read(qtbot):
    state = seed_app_state(profile_wrappers=read_profiles())
    state.device_service.set_template(THROTTLE, TEST_TEMPLATE)
    state.record_device_read()
    state.profile_wrappers = []  # a new session: nothing read yet
    page = ControllersPage()
    qtbot.addWidget(page)
    assert page.summary.snapshot
    assert page.stack.currentIndex() == 1
    assert THROTTLE in page.group_guids(GROUP_READY)
    assert STICK in page.group_guids(GROUP_NEEDS)


def test_more_section_name_and_copy(qtbot):
    page, state = make_page(qtbot, read_profiles())
    page.select_guid(STICK)
    page.more_button.setChecked(True)
    assert page.more.isVisibleTo(page)
    assert page.name_edit.placeholderText() == "Gladiator NXT"
    page.name_edit.setText("My stick")
    page.name_edit.editingFinished.emit()
    assert state.device_service.get_custom_name(STICK) == "My stick"
    assert page.id_label.text() == STICK
    page.copy_id.click()
    assert page.copy_id.text() == "Copied"
