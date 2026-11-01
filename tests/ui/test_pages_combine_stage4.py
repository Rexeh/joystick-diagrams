"""4. Diagrams › Pages: the Combine dialog's validation and Create → Export rows."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import os
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.render.page import Arrangement, SizePreset  # noqa: E402
from joystick_diagrams.ui import strings_diagrams as S  # noqa: E402
from joystick_diagrams.ui.device_setup import (  # noqa: E402
    controller_key,
    page_key,
    tick_key,
)
from joystick_diagrams.ui.diagrams_page import DiagramsPage  # noqa: E402
from joystick_diagrams.ui.pages_dialog import PagesDialog  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    PANEL,
    STICK,
    THROTTLE,
    FakeShell,
    _reset_app_state,
    seed_state,
    settings_store,
)


@pytest.fixture
def dialog(qapp, settings_store):
    seed_state()
    return PagesDialog(live_preview=False)


@pytest.mark.uitest
def test_only_ready_controllers_can_be_ticked(dialog):
    boxes = dialog.member_boxes
    assert boxes[STICK].isEnabled() and boxes[THROTTLE].isEnabled()
    assert not boxes[PANEL].isEnabled()
    assert boxes[PANEL].text() == "Button Box (needs a template)"


@pytest.mark.uitest
def test_validation_sentences_inline(dialog):
    assert not dialog.create_button.isEnabled()
    assert "at least 2 different controllers" in dialog.problems_label.text()
    dialog.member_boxes[STICK].setChecked(True)
    dialog.member_boxes[THROTTLE].setChecked(True)
    assert dialog.create_button.isEnabled()
    assert dialog.name_edit.text() == "Gladiator NXT + Warthog Throttle"
    dialog.name_edit.setText("")
    dialog._on_name_edited("")
    assert dialog.problems_label.text() == "A page needs a name."
    assert not dialog.create_button.isEnabled()
    dialog.name_edit.setText("Stick + Throttle")
    dialog.size_combo.setCurrentIndex(
        dialog.size_combo.findData(SizePreset.CUSTOM.value)
    )
    assert dialog.custom_widget.isVisibleTo(dialog)
    dialog.width_spin.setValue(0)
    assert "custom page size needs a width and a height" in dialog.problems_label.text()


@pytest.mark.uitest
def test_fields_and_copy(dialog):
    texts = [b.text() for b in dialog.arrangement_buttons.values()]
    assert texts == [S.ARRANGE_SIDE_BY_SIDE, S.ARRANGE_STACKED, S.ARRANGE_GRID]
    sizes = [dialog.size_combo.itemText(i) for i in range(dialog.size_combo.count())]
    assert sizes == ["A4", "Letter", "Kneeboard 5.5×8.5in", "Fit to content", "Custom…"]
    assert dialog.only_on_page.isChecked()
    assert dialog.only_on_page.text() == S.COMBINE_ONLY_ON_PAGE
    dialog.scale_slider.setValue(80)
    assert dialog.scale_label.text() == "80%"
    assert dialog.build_page().scale == pytest.approx(0.8)


@pytest.mark.uitest
def test_thumbnail_uses_the_first_profile(dialog):
    dialog.member_boxes[STICK].setChecked(True)
    dialog.member_boxes[THROTTLE].setChecked(True)
    wrapper = dialog.preview_profile()
    assert wrapper is not None and wrapper.profile_name == "F-16C"


@pytest.mark.uitest
def test_create_returns_to_export_with_the_page_ticked(qapp, settings_store):
    seed_state()
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    page.show_section("pages")

    def fake_exec(dialog):
        dialog.member_boxes[STICK].setChecked(True)
        dialog.member_boxes[THROTTLE].setChecked(True)
        dialog.rule_any.setChecked(True)  # every profile with one of them bound
        dialog.name_edit.setText("Stick + Throttle")
        dialog.arrangement_buttons[Arrangement.SIDE_BY_SIDE].setChecked(True)
        dialog.accept()
        return PagesDialog.DialogCode.Accepted

    with patch.object(PagesDialog, "exec", fake_exec):
        page.export_screen.combine_requested.emit()

    assert page.current_section() == "export"
    screen = page.export_screen
    created = page.appState.page_service.pages()[0]
    row = screen.model.row(page_key(created.page_id))
    assert row is not None and row.name == "Stick + Throttle"
    # F-16C (stick + throttle), A-10C (stick) and Common (throttle)
    assert [p.profile_name for p in row.profiles] == ["F-16C", "A-10C", "Common"]
    ticked = set(screen.export_list.ticked_keys())
    assert {p.tick_key for p in row.profiles} <= ticked
    stick = screen.model.row(controller_key(STICK))
    assert stick.on_page == "Stick + Throttle"
    assert tick_key(stick.key, "dcs world_f-16c") not in ticked
    assert screen.export_count() == 3
    assert shell.banners[-1][0] == S.PAGE_CREATED_BANNER
    item = screen.export_list.treeWidget.topLevelItem(1)
    assert item.text(2) == "(on Stick + Throttle page)"
    # Every stick profile is on the page: shown unticked and disabled
    for i in range(item.childCount()):
        child = item.child(i)
        assert child.checkState(0) == Qt.CheckState.Unchecked
        assert not child.flags() & Qt.ItemFlag.ItemIsEnabled
        assert child.text(2) == "(on Stick + Throttle page)"
    assert page.next_action().label == "Export 3 diagrams"
    # The page row says how many files it makes; empty controllers are named
    page_item = screen.export_list.treeWidget.topLevelItem(0)
    assert page_item.text(0).endswith("· 3 profiles")
    statuses = [page_item.child(i).text(2) for i in range(page_item.childCount())]
    assert statuses == [
        "",
        "⚠ Warthog Throttle drawn empty",
        "⚠ Gladiator NXT drawn empty",
    ]


# ── Make this page for (the profile rule) ──


@pytest.mark.uitest
def test_rule_counts_follow_the_ticked_controllers(dialog):
    from joystick_diagrams.render.page import ProfileRule

    assert dialog.rule_shared.isChecked()  # the default
    dialog.member_boxes[STICK].setChecked(True)
    dialog.member_boxes[THROTTLE].setChecked(True)
    assert dialog.rule_shared.text() == "Profiles that use both controllers · 1 profile"
    assert dialog.rule_any.text() == "Any profile that uses one of them · 3 profiles"
    assert dialog.build_page().profile_rule is ProfileRule.SHARED
    dialog._toggle_rule_list()
    assert dialog.rule_list.text() == "DCS World / F-16C"
    dialog.rule_any.setChecked(True)
    assert dialog.rule_list.text().splitlines() == [
        "DCS World / F-16C",
        "DCS World / A-10C — no Warthog Throttle bindings",
        "DCS World / Common — no Gladiator NXT bindings",
    ]
    assert dialog.build_page().profile_rule is ProfileRule.ANY
    dialog.member_boxes[THROTTLE].setChecked(False)
    assert "· 0 profiles" in dialog.rule_shared.text()


@pytest.mark.uitest
def test_create_is_disabled_when_no_profile_is_shared(qapp, settings_store):
    # The stick is bound only in A-10C, the throttle only in Common
    seed_state(
        profiles={
            "A-10C": {STICK: {1: ("Fire", [])}},
            "Common": {THROTTLE: {3: ("Comms", [])}},
        }
    )
    dialog = PagesDialog(live_preview=False)
    dialog.member_boxes[STICK].setChecked(True)
    dialog.member_boxes[THROTTLE].setChecked(True)
    assert not dialog.create_button.isEnabled()
    assert dialog.problems_label.text() == S.RULE_NONE_SHARED
    dialog.rule_any.setChecked(True)
    assert dialog.create_button.isEnabled()


@pytest.mark.uitest
def test_shared_page_exports_only_shared_profiles(qapp, settings_store):
    state = seed_state()
    created = state.page_service.create("Stick + Throttle", [STICK, THROTTLE])
    assert state.page_service.get(created.page_id).profile_rule.value == "shared"
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    row = page.export_screen.model.row(page_key(created.page_id))
    assert [p.profile_name for p in row.profiles] == ["F-16C"]
    item = page.export_screen.export_list.treeWidget.topLevelItem(0)
    assert item.text(0).endswith("· 1 profile")


@pytest.mark.uitest
def test_pages_screen_lists_rename_duplicate_delete(qapp, settings_store):
    state = seed_state()
    state.page_service.create("Stick + Throttle", [STICK, THROTTLE])
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.show_section("pages")
    screen = page.pages_screen
    assert screen.list.count() == 1
    assert screen.list.item(0).text() == (
        "Stick + Throttle\nSide by side · A4 landscape · 1 profile"
    )
    screen.duplicate_page()
    assert screen.list.count() == 2
    with patch(
        "joystick_diagrams.ui.pages_page.QInputDialog.getText",
        return_value=("Kneeboard", True),
    ):
        screen.rename_page()
    assert "Kneeboard" in [p.name for p in state.page_service.pages()]
    with (
        patch("joystick_diagrams.ui.pages_page.QMessageBox.exec"),
        patch(
            "joystick_diagrams.ui.pages_page.QMessageBox.clickedButton",
            return_value=None,
        ),
    ):
        screen.delete_page()  # cancelled
    assert screen.list.count() == 2
