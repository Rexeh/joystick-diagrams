"""4. Diagrams › Layout, page mode: the Page panel edits a page for real."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.render.page import (  # noqa: E402
    Arrangement,
    Orientation,
    Page,
    Placement,
    ProfileRule,
    SizePreset,
)
from joystick_diagrams.ui import customise_layout  # noqa: E402
from joystick_diagrams.ui import strings_layout as S  # noqa: E402
from joystick_diagrams.ui.customise_layout import CustomiseLayout  # noqa: E402
from joystick_diagrams.ui.pages_page import page_summary  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    STICK,
    THROTTLE,
    _reset_app_state,
    seed_state,
    settings_store,
)


@pytest.fixture
def layout(qapp, settings_store, monkeypatch):
    state = seed_state()
    page = state.page_service.create("Stick + Throttle", [STICK, THROTTLE])
    calls = []
    real = customise_layout.compose_page_result

    def spy(*args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    monkeypatch.setattr(customise_layout, "compose_page_result", spy)
    screen = CustomiseLayout()
    screen.refresh()
    screen.show_page(page.page_id)
    yield screen, state.page_service, page.page_id, calls
    screen.shutdown()


def _wait_for_render(qtbot, screen, calls, before: int):
    qtbot.waitUntil(lambda: len(calls) > before, timeout=5000)
    qtbot.waitUntil(lambda: not screen._page_render_timer.isActive(), timeout=5000)


@pytest.mark.uitest
def test_choosing_a_page_shows_the_page_panel_and_disables_box_tools(layout):
    screen, _service, _page_id, _calls = layout
    assert screen.canvas_stack.currentWidget() is screen.page_host
    assert screen.panel_stack.currentWidget() is screen.page_panel_scroll
    panel = screen.page_panel
    assert panel.name_edit.text() == "Stick + Throttle"
    names = [
        panel.controller_list.item(i).text()
        for i in range(panel.controller_list.count())
    ]
    assert names == ["Gladiator NXT", "Warthog Throttle"]
    for button in (
        screen.select_button,
        screen.add_box_button,
        screen.auto_add_button,
        screen.add_note_button,
        screen.hide_button,
    ):
        assert not button.isEnabled()
        assert button.toolTip() == S.PAGE_TOOL_UNAVAILABLE
    assert screen.zoom_in_button.isEnabled() and screen.fit_button.isEnabled()
    assert not screen.more_button.isVisibleTo(screen)
    assert not screen.scope_all.isVisibleTo(screen)
    # Preview with: only the profiles this page is made for
    texts = [
        screen.profile_combo.itemText(i) for i in range(screen.profile_combo.count())
    ]
    assert texts == ["DCS World / F-16C"]
    assert panel.rule_shared.isChecked()
    assert "1 profile" in panel.rule_shared.text_label.text()
    assert "3 profiles" in panel.rule_any.text_label.text()
    assert "F-16C · Stick + Throttle" in panel.title_edit.placeholderText()

    screen.show_device(STICK)  # back to a controller: the box tools return
    assert screen.panel_stack.currentWidget() is screen.box_panel
    assert screen.add_box_button.toolTip() == S.TOOLTIP_ADD_MODIFIER_BOX
    assert screen.add_box_button.isEnabled()


@pytest.mark.uitest
def test_field_changes_save_through_page_service_and_render_again(qtbot, layout):
    screen, service, page_id, calls = layout
    panel = screen.page_panel
    _wait_for_render(qtbot, screen, calls, 0)

    before = len(calls)
    panel.arrangement_buttons[Arrangement.STACKED].click()
    assert service.get(page_id).arrangement is Arrangement.STACKED
    assert screen._page_render_timer.isActive()
    _wait_for_render(qtbot, screen, calls, before)
    assert calls[-1].arrangement is Arrangement.STACKED

    before = len(calls)
    panel.size_combo.setCurrentIndex(panel.size_combo.findData(SizePreset.LETTER.value))
    panel.orientation_combo.setCurrentIndex(
        panel.orientation_combo.findData(Orientation.LANDSCAPE.value)
    )
    panel.scale_slider.setValue(60)
    panel.gap_spin.setValue(12)
    saved = service.get(page_id)
    assert saved.size_preset is SizePreset.LETTER
    assert saved.orientation is Orientation.LANDSCAPE
    assert saved.scale == pytest.approx(0.6)
    assert saved.gap_mm == pytest.approx(12)
    _wait_for_render(qtbot, screen, calls, before)
    assert calls[-1].scale == pytest.approx(0.6)  # debounced: the latest page

    panel.rule_any.click()
    assert service.get(page_id).profile_rule is ProfileRule.ANY
    assert screen.profile_combo.count() == 3  # Preview with follows the rule

    panel.show_title_check.setChecked(False)
    panel.show_date_check.setChecked(False)
    saved = service.get(page_id)
    assert not saved.show_title and not saved.show_date
    assert not panel.title_edit.isEnabled()
    panel.show_title_check.setChecked(True)
    panel.title_edit.setText("  Kneeboard   card ")
    panel.title_edit.editingFinished.emit()
    assert service.get(page_id).title == "Kneeboard card"


@pytest.mark.uitest
def test_undo_and_redo_one_step_per_change(layout):
    screen, service, page_id, _calls = layout
    panel = screen.page_panel
    assert not screen.undo_button.isEnabled()
    panel.gap_spin.setValue(10)
    panel.arrangement_buttons[Arrangement.GRID].click()
    assert screen.undo_button.isEnabled()
    screen.undo()
    assert service.get(page_id).arrangement is Arrangement.SIDE_BY_SIDE
    assert service.get(page_id).gap_mm == pytest.approx(10)
    assert panel.arrangement_buttons[Arrangement.SIDE_BY_SIDE].isChecked()
    screen.undo()
    assert service.get(page_id).gap_mm == pytest.approx(6)
    assert panel.gap_spin.value() == pytest.approx(6)
    assert not screen.undo_button.isEnabled() and screen.redo_button.isEnabled()
    screen.redo()
    assert service.get(page_id).gap_mm == pytest.approx(10)
    # A Ctrl+Z shortcut is live only in page mode
    assert all(s.isEnabled() for s in screen._page_shortcuts)
    screen.show_device(STICK)
    assert not any(s.isEnabled() for s in screen._page_shortcuts)


@pytest.mark.uitest
def test_reset_to_defaults_is_one_undo_step(layout):
    screen, service, page_id, _calls = layout
    panel = screen.page_panel
    panel.scale_slider.setValue(50)
    panel.size_combo.setCurrentIndex(panel.size_combo.findData(SizePreset.FIT.value))
    assert not panel.orientation_combo.isEnabled()
    panel.reset_button.click()
    saved = service.get(page_id)
    assert saved.scale == 1.0 and saved.size_preset is SizePreset.A4
    assert saved.name == "Stick + Throttle" and saved.member_guids == [STICK, THROTTLE]
    screen.undo()
    saved = service.get(page_id)
    assert saved.size_preset is SizePreset.FIT and saved.scale == pytest.approx(0.5)


@pytest.mark.uitest
def test_rename_updates_the_picker_and_bad_names_are_explained(layout):
    screen, service, page_id, _calls = layout
    panel = screen.page_panel
    panel.name_edit.setText("Kneeboard")
    panel.name_edit.editingFinished.emit()
    assert service.get(page_id).name == "Kneeboard"
    assert screen.diagram_combo.currentText() == "▣ Kneeboard"
    panel.name_edit.setText("   ")
    panel.name_edit.editingFinished.emit()
    assert service.get(page_id).name == "Kneeboard"
    assert panel.problem_label.text() == "A page needs a name."
    assert panel.name_edit.text() == "Kneeboard"


@pytest.mark.uitest
def test_edit_this_controllers_boxes_switches_the_picker(layout):
    screen, _service, _page_id, _calls = layout
    panel = screen.page_panel
    assert not panel.selection_box.isVisibleTo(panel)
    panel.select_controller(THROTTLE)
    assert panel.selection_box.isVisibleTo(panel)
    assert panel.selection_title.text() == "Warthog Throttle"
    assert panel.edit_boxes_button.text() == S.PAGE_EDIT_CONTROLLER_BOXES
    panel.edit_boxes_button.click()
    assert screen.current_page() is None
    assert screen.current_diagram().device_id == THROTTLE
    assert screen.panel_stack.currentWidget() is screen.box_panel


@pytest.mark.uitest
def test_change_controllers_is_one_undo_step(layout, monkeypatch):
    screen, service, page_id, _calls = layout
    page = service.get(page_id)

    def fake_dialog(_page):
        return service.save(page.model_copy(update={"name": "Pair", "scale": 0.7}))

    monkeypatch.setattr(screen, "open_page_dialog", fake_dialog)
    screen.page_panel.change_controllers_button.click()
    assert screen.page_panel.name_edit.text() == "Pair"
    screen.undo()
    assert service.get(page_id).name == "Stick + Throttle"


@pytest.mark.uitest
def test_small_text_highlights_scale_as_the_fix(layout):
    screen, _service, _page_id, _calls = layout
    panel = screen.page_panel
    warning = "Text on Gladiator NXT prints at 4.8 pt. Make it larger for readability."
    panel.scale_slider.setValue(70)
    panel.set_compose_result(SimpleNamespace(min_font_pt=4.8, warnings=(warning,)))
    assert panel.scale_frame.property("highlighted") is True
    assert panel.legibility_label.isVisibleTo(panel)
    assert panel.legibility_label.text() == f"{warning}\n{S.PAGE_FIX_SCALE}"
    assert panel.notice_texts() == []  # the sentence sits with Scale, its fix
    panel.scale_slider.setValue(100)
    panel.set_compose_result(SimpleNamespace(min_font_pt=4.8, warnings=(warning,)))
    assert panel.legibility_label.text().endswith(S.PAGE_FIX_AT_FULL_SCALE)
    other = "Warthog Throttle does not fit on the page."
    panel.set_compose_result(SimpleNamespace(min_font_pt=8.0, warnings=(other,)))
    assert panel.notice_texts() == [other]
    panel.set_compose_result(SimpleNamespace(min_font_pt=8.0, warnings=()))
    assert panel.scale_frame.property("highlighted") is False
    assert not panel.legibility_label.isVisibleTo(panel)
    assert panel.no_notices.isVisibleTo(panel)


@pytest.mark.uitest
def test_a_real_render_reports_into_the_panel(layout):
    screen, _service, _page_id, _calls = layout
    result = screen._render_page(synchronous=True)
    assert result is not None and result.min_font_pt
    assert screen.page_compose_result is result
    panel = screen.page_panel
    shown = panel.notice_texts() + panel.legibility_label.text().split("\n")
    assert all(warning in shown for warning in result.warnings)


def test_pages_row_summary_is_arrangement_size_and_profiles():
    page = Page(
        name="Stack",
        arrangement=Arrangement.STACKED,
        size_preset=SizePreset.LETTER,
        placements=[Placement(device_guid=STICK), Placement(device_guid=THROTTLE)],
    )
    assert page_summary(page, 3) == "Stacked · Letter portrait · 3 profiles"
    assert page_summary(page, 1).endswith("· 1 profile")
