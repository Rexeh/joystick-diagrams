"""StageTab / StageChevron: the icon shape carries the state; tabs never lock."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

from joystick_diagrams.ui.stage_contract import StageStatus  # noqa: E402
from joystick_diagrams.ui.widgets.stage_tab import (  # noqa: E402
    STATUS_ICONS,
    StageChevron,
    StageTab,
)


@pytest.fixture
def tab(qtbot):
    widget = StageTab(0, "1. Setup", "fa5s.cog")
    qtbot.addWidget(widget)
    return widget


def test_title_is_upper_case_and_status_starts_empty(tab):
    assert tab.title_label.text() == "1. SETUP"
    assert tab.state == "none"
    assert tab.status_icon.isHidden()


@pytest.mark.parametrize("state", ["ok", "warning", "error", "busy"])
def test_each_state_sets_the_property_and_shows_its_icon(tab, state):
    tab.set_status(StageStatus(state, "Up to date · read 09:41"))
    assert tab.property("state") == state
    assert tab.status_label.text() == "Up to date · read 09:41"
    assert not tab.status_icon.isHidden()
    assert STATUS_ICONS[state][0] is not None


def test_none_state_hides_the_icon_and_unknown_falls_back(tab):
    tab.set_status(StageStatus("ok", "Done"))
    tab.set_status(StageStatus("none", "Optional"))
    assert tab.status_icon.isHidden()
    tab.set_status(StageStatus("bogus", "x"))  # type: ignore[arg-type]
    assert tab.state == "none"


def test_icon_shapes_differ_per_state():
    shapes = {STATUS_ICONS[s][0] for s in ("ok", "warning", "error", "busy")}
    assert shapes == {
        "fa5s.check-circle",
        "fa5s.exclamation-triangle",
        "fa5s.times-circle",
        "fa5s.sync",
    }


def test_active_property_and_accessible_name(tab):
    tab.set_status(StageStatus("warning", "4 need a template"))
    tab.set_active(True)
    assert tab.property("active") == "true"
    assert tab.is_active
    assert tab.accessibleName() == "1. Setup, 4 need a template"
    tab.set_active(False)
    assert tab.property("active") == "false"


def test_click_and_keyboard_emit_the_index(tab, qtbot):
    tab.setEnabled(True)
    with qtbot.waitSignal(tab.clicked) as blocker:
        qtbot.mouseClick(tab, Qt.MouseButton.LeftButton)
    assert blocker.args == [0]
    with qtbot.waitSignal(tab.clicked):
        qtbot.keyClick(tab, Qt.Key.Key_Return)
    assert tab.isEnabled()


def test_status_done_flag_overrides_the_icon():
    assert StageStatus("ok", "x").is_done
    assert not StageStatus("warning", "x").is_done
    assert StageStatus("none", "Optional · 12 profiles", done=True).is_done


def test_chevron_turns_green_when_done(qtbot):
    chevron = StageChevron()
    qtbot.addWidget(chevron)
    assert not chevron.is_done
    chevron.set_done(True)
    assert chevron.is_done
    assert "completed" in chevron.property("class")
