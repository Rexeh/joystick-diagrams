"""Plain-language summary of an export batch (plan §1.5 reporting).

``ExportDispatch`` collects one ``ExportEntry`` per rendered diagram (its
``RenderReport``); ``build_summary`` turns them into the short text shown in
the "Export Completed" dialog plus a detailed per-diagram list. Pure Python so
the wording can be unit-tested.
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
from joystick_diagrams.ui import strings_layout as S


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


def _reason_for_fallback(report: RenderReport) -> str:
    if RenderNotice.PARSE_ERROR in report.notices:
        return S.REASON_PARSE_ERROR
    if RenderNotice.NOT_DRAWIO in report.notices:
        return S.REASON_NOT_DRAWIO
    if RenderNotice.COVERAGE_MISMATCH in report.notices:
        return S.REASON_COVERAGE
    return S.REASON_UNEXPECTED


def styled_context(ctx: RenderContext | None) -> bool:
    return ctx is not None and (ctx.theme is not None or ctx.colour_modifiers)


@dataclass
class _Tally:
    fell_back: int = 0
    limited: int = 0
    overflow_controls: int = 0
    skipped: int = 0
    unplaced: int = 0
    details: list[str] = field(default_factory=list)


def _tally_entry(tally: _Tally, entry: ExportEntry, styled: bool) -> None:
    report = entry.report
    if report is None:
        return
    reasons: list[str] = []
    if RenderNotice.FELL_BACK_TO_LEGACY in report.notices:
        if styled:
            tally.fell_back += 1
            reasons.append(_reason_for_fallback(report))
    elif report.engine is Engine.DOM:
        if Capability.SHAPE_STYLE not in report.capabilities and styled:
            tally.limited += 1
            reasons.append(S.REASON_TEXT_ONLY)
        if report.skipped_ops:
            n = len(report.skipped_ops)
            tally.skipped += n
            reasons.append(S.REASON_SKIPPED.format(count=n, s=S.plural(n)))
        if RenderNotice.BOXES_UNPLACED in report.notices:
            tally.unplaced += 1
            reasons.append(S.REASON_UNPLACED.format(count="some", es="es"))
    if report.overflow:
        n = len(report.overflow)
        tally.overflow_controls += n
        reasons.append(S.REASON_OVERFLOW.format(count=n, s=S.plural(n)))
    if reasons:
        tally.details.append(
            S.SUMMARY_DETAIL_LINE.format(
                device=entry.device_name,
                profile=entry.profile_name,
                reason="; ".join(reasons),
            )
        )


def _tally_lines(tally: _Tally, modifiers_listed: bool) -> list[str]:
    lines: list[str] = []
    if tally.fell_back:
        n = tally.fell_back
        lines.append(
            S.SUMMARY_STYLE_FAILED.format(
                count=n, s=S.plural(n), they=S.plural(n, "It was", "They were")
            )
        )
    if tally.limited:
        n = tally.limited
        lines.append(S.SUMMARY_STYLE_LIMITED.format(count=n, s=S.plural(n)))
    if tally.overflow_controls:
        n = tally.overflow_controls
        template = (
            S.SUMMARY_OVERFLOW_LISTED if modifiers_listed else S.SUMMARY_OVERFLOW_HIDDEN
        )
        lines.append(template.format(count=n, s=S.plural(n)))
    if tally.skipped:
        n = tally.skipped
        lines.append(
            S.SUMMARY_LAYOUT_SKIPPED.format(
                count=n, s=S.plural(n), was=S.plural(n, "was", "were")
            )
        )
    if tally.unplaced:
        n = tally.unplaced
        lines.append(
            S.SUMMARY_BOXES_UNPLACED.format(
                count=n, es=S.plural(n, "", "es"), was=S.plural(n, "was", "were")
            )
        )
    return lines


def build_summary(summary: ExportSummary, location: str) -> tuple[str, str]:
    """``(text, details)`` for the completed dialog."""
    count = summary.count
    lines = [
        S.SUMMARY_EXPORTED.format(count=count, s=S.plural(count), location=location)
    ]
    tally = _Tally()
    for entry in summary.entries:
        _tally_entry(tally, entry, summary.styled)
    lines.extend(_tally_lines(tally, summary.modifiers_listed))
    if len(lines) == 1:
        lines.append(S.SUMMARY_ALL_GOOD)
    return "\n\n".join(lines), "\n".join(tally.details)


def entry_for(export_device: Any, report: RenderReport | None) -> ExportEntry:
    return ExportEntry(
        device_name=str(getattr(export_device, "device_name", "")),
        profile_name=str(getattr(export_device.profile_wrapper, "profile_name", "")),
        report=report,
    )


if __name__ == "__main__":
    pass
