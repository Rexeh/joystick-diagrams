"""Export summary wording (plan §1.5 reporting) and the Export page hook."""

import os
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.render import (  # noqa: E402
    Capability,
    Engine,
    RenderContext,
    RenderNotice,
    RenderReport,
)
from joystick_diagrams.ui import strings_layout as S  # noqa: E402
from joystick_diagrams.ui.export_summary import (  # noqa: E402
    ExportEntry,
    ExportSummary,
    build_summary,
    styled_context,
)


def entry(name, profile, report):
    return ExportEntry(name, profile, report)


def test_all_good_summary():
    summary = ExportSummary(
        count=2, entries=[entry("X56", "F-16", RenderReport(Engine.LEGACY))]
    )
    text, details = build_summary(summary, "/out")
    assert text.startswith("2 items exported to /out")
    assert S.SUMMARY_ALL_GOOD in text and details == ""


def test_style_fallback_and_limited_wording_only_when_styled():
    fell_back = RenderReport(
        Engine.LEGACY,
        notices=(RenderNotice.NOT_DRAWIO, RenderNotice.FELL_BACK_TO_LEGACY),
    )
    limited = RenderReport(
        Engine.DOM,
        capabilities=frozenset({Capability.TEXT, Capability.TEXT_STYLE}),
        notices=(RenderNotice.ALIGNMENT_DEGRADED,),
    )
    entries = [
        entry("X56 Throttle", "F-16", fell_back),
        entry("Stick", "F-18", limited),
    ]
    text, details = build_summary(ExportSummary(2, entries, styled=True), "/out")
    assert (
        "Your style couldn't be applied to 1 diagram. It was exported with the original look."
        in text
    )
    assert "1 diagram only took text styling" in text
    assert "X56 Throttle · F-16: this template wasn't made with draw.io" in details
    assert "Stick · F-18: boxes and lines couldn't be matched" in details

    text, details = build_summary(ExportSummary(2, entries, styled=False), "/out")
    assert "style" not in text.lower() and details == ""


def test_overflow_skipped_and_unplaced_wording():
    report = RenderReport(
        Engine.DOM,
        capabilities=frozenset(Capability),
        notices=(RenderNotice.LAYOUT_OPS_SKIPPED, RenderNotice.BOXES_UNPLACED),
        overflow=MappingProxyType({"BUTTON_1": 2, "BUTTON_2": 1}),
        skipped_ops=("a", "b", "c"),
    )
    summary = ExportSummary(1, [entry("Stick", "F-16", report)], modifiers_listed=True)
    text, details = build_summary(summary, "/out")
    assert "2 controls had more modifiers than boxes; nothing is missing" in text
    assert "3 layout changes were skipped because the template changed." in text
    assert "1 modifier box had no room and was left out." in text
    assert "Stick · F-16: 3 layout changes skipped" in details

    summary.modifiers_listed = False
    text, _ = build_summary(summary, "/out")
    assert "the extra modifiers aren't shown" in text


def test_styled_context_detection():
    assert not styled_context(None)
    assert not styled_context(RenderContext())
    assert styled_context(RenderContext(colour_modifiers=True))
    assert styled_context(RenderContext(theme=object()))


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


@pytest.mark.uitest
def test_export_page_dialog_uses_summary_and_open_folder_button(qapp):
    from joystick_diagrams.app_state import AppState
    from joystick_diagrams.ui.export_page import ExportPage

    manager = MagicMock()
    manager.plugin_wrappers = []
    manager.get_enabled_plugin_wrappers.return_value = []
    output = MagicMock()
    output.get_enabled_plugin_wrappers.return_value = []
    state = AppState(plugin_manager=manager, output_plugin_manager=output)
    state.main_window = MagicMock()
    page = ExportPage()
    page.export_settings_widget.export_location = "/tmp/out"

    report = RenderReport(
        Engine.LEGACY,
        notices=(RenderNotice.PARSE_ERROR, RenderNotice.FELL_BACK_TO_LEGACY),
    )
    page._on_export_summary(
        ExportSummary(1, [entry("Stick", "F-16", report)], styled=True)
    )
    shown = {}

    def fake_exec(box):
        shown["text"] = box.text()
        shown["details"] = box.detailedText()
        shown["buttons"] = [b.text() for b in box.buttons()]
        return 0

    with (
        patch("joystick_diagrams.ui.export_page.QMessageBox.exec", fake_exec),
        patch("joystick_diagrams.ui.export_page.webbrowser.open") as opened,
    ):
        page.export_finished(1)
    assert "Your style couldn't be applied to 1 diagram" in shown["text"]
    assert "isn't valid SVG/XML" in shown["details"]
    assert {S.SUMMARY_OPEN_FOLDER, S.SUMMARY_DONE} <= set(shown["buttons"])
    assert opened.call_count == 1  # open_after_export defaults on
    assert page._last_summary is None
