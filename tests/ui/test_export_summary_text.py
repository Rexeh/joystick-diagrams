"""Export result wording: the inline result line and "Check before you print"."""

import os
from types import MappingProxyType

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.render import (  # noqa: E402
    Capability,
    Engine,
    RenderContext,
    RenderNotice,
    RenderReport,
)
from joystick_diagrams.ui.export_summary import (  # noqa: E402
    ExportEntry,
    ExportSummary,
    check_notices,
    styled_context,
)


def entry(name, profile, report):
    return ExportEntry(name, profile, report)


def test_nothing_to_check_when_all_good():
    summary = ExportSummary(
        count=2, entries=[entry("X56", "F-16", RenderReport(Engine.LEGACY))]
    )
    assert check_notices(summary) == []


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
    lines = check_notices(ExportSummary(2, entries, styled=True))
    assert lines == [
        "1 diagram was exported without your style: its template can't take styles.",
        "Only the text took your style on 1 diagram; its boxes and lines keep their look.",
    ]
    assert check_notices(ExportSummary(2, entries, styled=False)) == []


def test_overflow_skipped_and_unplaced_wording():
    report = RenderReport(
        Engine.DOM,
        capabilities=frozenset(Capability),
        notices=(RenderNotice.LAYOUT_OPS_SKIPPED, RenderNotice.BOXES_UNPLACED),
        overflow=MappingProxyType({"BUTTON_1": 2, "BUTTON_2": 1}),
        skipped_ops=("a", "b", "c"),
    )
    summary = ExportSummary(1, [entry("Stick", "F-16", report)], modifiers_listed=True)
    lines = check_notices(summary)
    assert (
        "2 controls had more modifier bindings than boxes; the extra ones are "
        "listed under the main text."
    ) in lines
    assert "3 layout changes were skipped because the template changed." in lines
    assert "1 modifier box had no room and was left out." in lines

    summary.modifiers_listed = False
    assert any("the extra ones aren't shown" in line for line in check_notices(summary))


def test_labels_too_long_even_at_the_smallest_size():
    def report(*keys):
        return RenderReport(
            Engine.DOM,
            capabilities=frozenset(Capability),
            text_overflow=tuple((key, "long text") for key in keys),
        )

    one = ExportSummary(1, [entry("VKB", "F-16", report("button_12"))])
    assert check_notices(one) == [
        "1 label is too long for its box even at the smallest size: Button 12."
    ]
    # Each box counts once, whatever the profile.
    three = ExportSummary(
        2,
        [
            entry("VKB", "F-16", report("button_12", "button_4")),
            entry("VKB", "F-18", report("button_12", "pov_1_u")),
        ],
    )
    assert check_notices(three) == [
        "3 labels are too long for their boxes even at the smallest size: "
        "Button 12, Button 4 and Hat 1 Up."
    ]
    # Two controllers: each name says which.
    two = ExportSummary(
        2,
        [
            entry("VKB", "F-16", report("button_12")),
            entry("Throttle", "F-16", report("button_1")),
        ],
    )
    assert check_notices(two) == [
        "2 labels are too long for their boxes even at the smallest size: "
        "Button 12 on VKB and Button 1 on Throttle."
    ]
    many = ExportSummary(
        1, [entry("VKB", "F-16", report(*(f"button_{n}" for n in range(1, 10))))]
    )
    (line,) = check_notices(many)
    assert line.startswith("9 labels are too long") and line.endswith(
        "Button 4, Button 5 and 4 more."
    )


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


def test_inline_result_line_and_check_notices():
    from joystick_diagrams.ui.export_summary import (
        check_notices,
        gap_notice,
        result_line,
    )

    report = RenderReport(
        Engine.LEGACY,
        notices=(RenderNotice.PARSE_ERROR, RenderNotice.FELL_BACK_TO_LEGACY),
    )
    summary = ExportSummary(1, [entry("Stick", "F-16", report)], styled=True)
    assert result_line(summary, "D:/Kneeboards") == "1 diagram saved to D:/Kneeboards"
    summary.total, summary.count = 3, 2
    assert result_line(summary, "X") == "2 of 3 diagrams saved to X."
    assert check_notices(summary) == [
        "1 diagram was exported without your style: its template can't take styles."
    ]
    assert gap_notice("VPC", ["button_31", "button_32", "pov_3_u"]) == (
        "VPC: 3 bindings won't show because the template has no box for "
        "Button 31, Button 32 or Hat 3 Up."
    )
