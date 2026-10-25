"""Plain-language summary of an export batch (plan §1.5 reporting).

``ExportDispatch`` collects one ``ExportEntry`` per rendered diagram (its
``RenderReport``). ``result_line`` is the inline "33 diagrams saved to <folder>"
line on the Export screen and ``check_notices`` the sentences of its "Check
before you print" block (journey board J09): bindings that won't show, styles
that couldn't be applied, modifier overflow, skipped layout changes and page
warnings. Pure Python so the wording can be unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from joystick_diagrams.render import (
    Capability,
    Engine,
    RenderContext,
    RenderNotice,
    RenderReport,
)
from joystick_diagrams.ui import strings_diagrams as D


@dataclass(frozen=True)
class ExportEntry:
    device_name: str
    profile_name: str
    report: RenderReport | None


@dataclass
class ExportSummary:
    count: int = 0
    entries: list[ExportEntry] = field(default_factory=list)
    styled: bool = False  # the context asked for something the DOM engine does
    modifiers_listed: bool = False  # overflowed modifiers appear under the main text
    total: int = 0  # diagrams asked for (count is how many were written)
    failed: int = 0  # diagrams that couldn't be made (details in the log)
    page_warnings: list[str] = field(default_factory=list)


def styled_context(ctx: RenderContext | None) -> bool:
    return ctx is not None and (ctx.theme is not None or ctx.colour_modifiers)


@dataclass
class _Tally:
    fell_back: int = 0
    limited: int = 0
    overflow_controls: int = 0
    skipped: int = 0
    unplaced: int = 0


def _tally_entry(tally: _Tally, entry: ExportEntry, styled: bool) -> None:
    report = entry.report
    if report is None:
        return
    if RenderNotice.FELL_BACK_TO_LEGACY in report.notices:
        if styled:
            tally.fell_back += 1
    elif report.engine is Engine.DOM:
        if Capability.SHAPE_STYLE not in report.capabilities and styled:
            tally.limited += 1
        if report.skipped_ops:
            tally.skipped += len(report.skipped_ops)
        if RenderNotice.BOXES_UNPLACED in report.notices:
            tally.unplaced += 1
    if report.overflow:
        tally.overflow_controls += len(report.overflow)


def result_line(summary: ExportSummary, folder: str) -> str:
    """ "33 diagrams saved to D:\\Kneeboards" (or "31 of 33 … saved to …")."""
    count = summary.count
    total = max(summary.total, count)
    if total and count < total:
        line = D.RESULT_SAVED_PARTIAL.format(
            count=count,
            total=total,
            diagrams=D.plural(total, *D.DIAGRAMS),
            folder=folder,
        )
    else:
        line = D.RESULT_SAVED.format(
            count=count, diagrams=D.plural(count, *D.DIAGRAMS), folder=folder
        )
    if summary.failed:
        line += " " + D.RESULT_FAILED_SOME.format(count=summary.failed)
    return line


def gap_notice(controller: str, missing: list[str]) -> str:
    """ "VPC: 3 bindings won't show because the template has no box for Button 31,
    Button 32 or Hat 3 Up." """
    from joystick_diagrams.template_catalog import control_label

    count = len(missing)
    return D.NOTICE_GAPS.format(
        controller=controller,
        count=count,
        bindings=D.plural(count, *D.BINDINGS),
        controls=D.join_names([control_label(m) for m in missing]),
    )


def check_notices(summary: ExportSummary) -> list[str]:
    """The render-side sentences for "Check before you print" (empty: nothing to check)."""
    tally = _Tally()
    for entry in summary.entries:
        _tally_entry(tally, entry, summary.styled)
    lines: list[str] = []
    if tally.fell_back:
        n = tally.fell_back
        lines.append(
            D.NOTICE_STYLE_FAILED.format(
                count=n,
                diagrams=D.plural(n, *D.DIAGRAMS),
                were=D.plural(n, "was", "were"),
                their=D.plural(n, "its template", "their templates"),
            )
        )
    if tally.limited:
        n = tally.limited
        lines.append(
            D.NOTICE_STYLE_LIMITED.format(
                count=n,
                diagrams=D.plural(n, *D.DIAGRAMS),
                their=D.plural(n, "its", "their"),
            )
        )
    if tally.overflow_controls:
        n = tally.overflow_controls
        template = (
            D.NOTICE_OVERFLOW_LISTED
            if summary.modifiers_listed
            else D.NOTICE_OVERFLOW_HIDDEN
        )
        lines.append(template.format(count=n, controls=D.plural(n, *D.CONTROLS)))
    if tally.skipped:
        n = tally.skipped
        lines.append(
            D.NOTICE_LAYOUT_SKIPPED.format(
                count=n,
                changes=D.plural(n, *D.CHANGES),
                were=D.plural(n, "was", "were"),
            )
        )
    if tally.unplaced:
        n = tally.unplaced
        lines.append(
            D.NOTICE_BOXES_UNPLACED.format(
                count=n, boxes=D.plural(n, *D.BOXES), were=D.plural(n, "was", "were")
            )
        )
    lines.extend(dict.fromkeys(summary.page_warnings))
    return lines


def entry_for(export_device: Any, report: RenderReport | None) -> ExportEntry:
    return ExportEntry(
        device_name=str(getattr(export_device, "device_name", "")),
        profile_name=str(getattr(export_device.profile_wrapper, "profile_name", "")),
        report=report,
    )


if __name__ == "__main__":
    pass
