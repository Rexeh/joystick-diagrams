"""Modifier presentation: the ``style`` hook that writes rich modifier text (plan §2.2C/G/H).

After the fill stage every slot holds plain text. This hook asks the resolver
for the *rich* version of each single-token slot (``BindingResolver.rich_for``)
and, when it differs from plain text, rewrites the slot's three surfaces:

- the innermost foreignObject ``<div>`` (or the deepest single wrapper inside it,
  so ``<font style="font-size: 9px">`` in the VKB templates keeps its size):
  one ``<div>`` per line (carrying the line's relative size, as draw.io's own
  multi-line labels do), coloured runs as ``<span style="color: …">``;
- the ``<text>`` fallback: one ``<tspan x dy>`` per line, coloured runs as
  nested ``<tspan fill>``;
- the draw.io model label: ``html=1`` with escaped ``<br>``/``<font color>``
  markup, so the export reopens in draw.io looking the same.

Modifier boxes (``*_MODIFIER_N``, ``_KEY``, ``_ACTION``) also take the stroke
colour of their binding's highest-priority key when "Colour by modifier key" is
on. Key text is always printed, so colour never carries meaning alone.

Text fit (spike S5, ``render/text_fit.py``, ``render/slot_fit.py``)
-----------------------------------------------------------------
Before a rich label is written it is fitted to its box: the font the template
or theme decided (read back from the innermost div, after the theme writer ran)
is shrunk down to the role's ``min_font_size`` until the wrapped block fits the
box, and when even that is not enough the trailing modifier lines are replaced
by ``+N more``. The chosen size is written to all three surfaces (the host
div's ``font-size``, the ``<text>`` attribute, the cell's ``fontSize``) so the
SVG, Inkscape and draw.io agree; dropped lines are reported through
``RenderReport.overflow`` and ``details``.

Under "Auto" (``TextStyle.fit == "auto"``) the same fit also runs for every
other label (``write_plain_fit``): plain bindings, merged text and
multi-token labels take the largest size that fits their box, up to the
role's ceiling (``slot_fit.auto_ceiling``). Their foreignObject markup is kept
and only takes the size; the ``<text>`` fallback gets the wrapped lines; the
cell gets ``fontSize``. A label too long even at the minimum is written at the
minimum, never shortened, and listed in ``RenderReport.text_overflow``.
Original (unchanged) never gets here (the legacy engine renders) and the
other fit modes leave plain labels as the template drew them.
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Any

from lxml import etree

from joystick_diagrams.render.adapters._common import SVG, XHTML
from joystick_diagrams.render.binding import Line, RichText, Run
from joystick_diagrams.render.drawio_model import MxCell
from joystick_diagrams.render.slot_fit import (
    apply_fit_to_div,
    content_host,
    css_px,
    fit_for_slot,
    foreign_box_width,
    foreign_font,
    is_auto,
    label_centre,
    painted_frames,
    slot_fit_box,
    slot_plain_text,
    visible_frame,
)
from joystick_diagrams.render.slots import (
    Capability,
    Rect,
    Slot,
    SlotRole,
    TextTarget,
    TextTargetKind,
)
from joystick_diagrams.render.style_writer import (
    format_declarations,
    style_cell_box,
    style_shape,
)
from joystick_diagrams.render.text_fit import FitResult, line_em
from joystick_diagrams.render.theme import BoxStyle

if TYPE_CHECKING:
    from joystick_diagrams.render.pipeline import RenderJob

BOX_SLOT_ROLES = frozenset(
    {SlotRole.MODIFIER, SlotRole.MODIFIER_KEY, SlotRole.MODIFIER_ACTION}
)
LINE_HEIGHT_EM = 1.2
_LABEL_FONT_SIZE_RE = re.compile(r"font-size:\s*[^;\"']*;?\s*", re.IGNORECASE)
_LABEL_FONT_ATTR_RE = re.compile(
    r"(<font\b[^>]*?)\s+size=(\"[^\"]*\"|'[^']*'|\S+)", re.IGNORECASE
)
_EMPTY_STYLE_RE = re.compile(r"\s+style=(\"\s*\"|'\s*')")


def _font_size_px(value: float) -> str:
    return f"{value:g}px"


# ── foreignObject ──


def _clear(element: Any) -> None:
    element.text = None
    for child in list(element):
        element.remove(child)


def _append_text(host: Any, text: str) -> None:
    children = list(host)
    if children:
        children[-1].tail = (children[-1].tail or "") + text
    else:
        host.text = (host.text or "") + text


def _run_declarations(run: Run) -> dict[str, str]:
    declarations: dict[str, str] = {}
    if run.colour is not None:
        declarations["color"] = run.colour
    if run.bold:
        declarations["font-weight"] = "bold"
    if run.size_em is not None:
        declarations["font-size"] = f"{run.size_em:g}em"
    return declarations


def _append_html_run(host: Any, run: Run) -> None:
    declarations = _run_declarations(run)
    if not declarations:
        _append_text(host, run.text)
        return
    span = etree.SubElement(host, f"{XHTML}span")
    span.set("style", format_declarations(declarations).strip())
    span.text = run.text


def _line_runs(line: Line, em: float) -> Line:
    """The runs of a line whose shared size ``em`` moved onto the line's block."""
    if em == 1.0 and all(run.size_em is None for run in line):
        return line
    return tuple(Run(run.text, run.colour, run.bold, None) for run in line)


def _append_html_line(host: Any, line: Line) -> None:
    block = etree.SubElement(host, f"{XHTML}div")
    em = line_em(line)
    if em != 1.0:
        block.set("style", f"font-size: {em:g}em;")
    for run in _line_runs(line, em):
        _append_html_run(block, run)


def write_foreign_object(
    div: Any, rich: RichText, fit: FitResult | None = None
) -> None:
    """One block per line; a single line is written inline, as the template had it."""
    host = content_host(div)
    _clear(host)
    if len(rich.lines) == 1:
        for run in rich.lines[0]:
            _append_html_run(host, run)
    else:
        for line in rich.lines:
            _append_html_line(host, line)
    if fit is not None:
        apply_fit_to_div(div, fit)


# ── <text> fallback ──


def _append_svg_run(parent: Any, run: Run) -> None:
    if run.is_plain:
        _append_text(parent, run.text)
        return
    tspan = etree.SubElement(parent, f"{SVG}tspan")
    if run.colour is not None:
        tspan.set("fill", run.colour)
    if run.bold:
        tspan.set("font-weight", "bold")
    if run.size_em is not None:
        tspan.set("font-size", f"{run.size_em:g}em")
    tspan.text = run.text


def _line_tspan(
    text_element: Any,
    index: int,
    ems: list[float],
    line_height: float = LINE_HEIGHT_EM,
) -> Any:
    """A line's ``<tspan x dy font-size>``; ``dy`` is in the tspan's own em."""
    tspan = etree.SubElement(text_element, f"{SVG}tspan")
    x = text_element.get("x")
    if x is not None:
        tspan.set("x", x)
    em = ems[index]
    if em != 1.0:
        tspan.set("font-size", f"{em:g}em")
    if index == 0:
        # Keep the block vertically centred on the original baseline.
        following = sum(ems[1:]) * line_height
        tspan.set("dy", f"{-following / 2 / em:g}em")
    else:
        tspan.set("dy", f"{line_height:g}em")
    return tspan


def write_text_element(
    text_element: Any, rich: RichText, fit: FitResult | None = None
) -> None:
    """Write ``rich`` as tspans; with a ``fit``, its word-wrapped lines and size."""
    _clear(text_element)
    lines = fit.wrapped if fit is not None else rich.lines
    line_height = fit.line_height if fit is not None else LINE_HEIGHT_EM
    if fit is not None and css_px(text_element.get("font-size")) != fit.font_size:
        text_element.set("font-size", _font_size_px(fit.font_size))
    if len(lines) == 1:
        for run in lines[0]:
            _append_svg_run(text_element, run)
        return
    ems = [line_em(line) for line in lines]
    for index, line in enumerate(lines):
        tspan = _line_tspan(text_element, index, ems, line_height)
        for run in _line_runs(line, ems[index]):
            _append_svg_run(tspan, run)


def write_text_target(
    target: TextTarget, rich: RichText, fit: FitResult | None = None
) -> None:
    if target.kind is TextTargetKind.FOREIGN_OBJECT:
        write_foreign_object(target.element, rich, fit)
    else:
        write_text_element(target.element, rich, fit)


# ── draw.io model label ──


def _html_run(run: Run) -> str:
    text = html.escape(run.text, quote=False)
    if run.bold:
        text = f"<b>{text}</b>"
    if run.size_em is not None:
        text = f'<span style="font-size: {run.size_em:g}em">{text}</span>'
    if run.colour is not None:
        text = f'<font color="{run.colour}">{text}</font>'
    return text


def _html_line(line: Line) -> str:
    return "".join(_html_run(run) for run in line)


def rich_html(rich: RichText) -> str:
    """The ``html=1`` label markup for a draw.io cell."""
    return "<br>".join(_html_line(line) for line in rich.lines)


def write_cell_label(
    cell: MxCell, rich: RichText, fit: FitResult | None = None
) -> None:
    style = cell.style_dict
    changed = False
    if style.get("html") != "1":
        style["html"] = "1"
        changed = True
    if fit is not None and style.get("fontSize") != f"{fit.font_size:g}":
        style["fontSize"] = f"{fit.font_size:g}"
        changed = True
    if changed:
        cell.set_style_dict(style)
    label = rich_html(rich)
    if fit is not None and fit.compact:
        label = f'<div style="line-height: {fit.line_height:g}">{label}</div>'
    cell.set_label(label)


def strip_label_font_sizes(label: str) -> str:
    """An ``html=1`` label without its own font sizes, so the cell's ``fontSize`` rules."""
    label = _LABEL_FONT_SIZE_RE.sub("", label)
    label = _LABEL_FONT_ATTR_RE.sub(r"\1", label)
    return _EMPTY_STYLE_RE.sub("", label)


def fit_cell_label(cell: MxCell, fit: FitResult) -> None:
    """Write a plain label's fitted size to the model, keeping the template's markup."""
    style = cell.style_dict
    if style.get("fontSize") != f"{fit.font_size:g}":
        style["fontSize"] = f"{fit.font_size:g}"
        cell.set_style_dict(style)
    if not cell.is_html:
        return
    label = strip_label_font_sizes(cell.label)
    if fit.compact:
        label = f'<div style="line-height: {fit.line_height:g}">{label}</div>'
    if label != cell.label:
        cell.set_label(label)


# ── Hook ──


def _overflow_for(job: RenderJob, slot: Slot) -> int:
    if slot.input_key is None or slot.role is not SlotRole.ACTION:
        return 0
    return job.overflow.get(slot.input_key.upper(), 0)


def record_text_overflow(job: RenderJob, slot: Slot, text: str) -> None:
    """Note a label that is too long for its box even at the smallest size."""
    if all(key != slot.key for key, _ in job.text_overflow):
        job.text_overflow.append((slot.key, text))
    job.details.append(
        f"{slot.key.upper()}: text overflows its box at the smallest size"
    )


def _record_truncation(
    job: RenderJob, slot: Slot, fit: FitResult, rich: RichText
) -> None:
    if fit.truncated and slot.input_key is not None:
        key = slot.input_key.upper()
        job.overflow[key] = max(job.overflow.get(key, 0), fit.truncated)
    if fit.truncated:
        job.details.append(
            f"{slot.key.upper()}: {fit.truncated} modifier line(s) hidden "
            f"(box too small at {fit.font_size:g}px)"
        )
    if not fit.fits:
        record_text_overflow(job, slot, rich.plain(" "))


def _writes_text(job: RenderJob) -> bool:
    assert job.slots is not None
    capabilities = job.slots.capabilities
    return Capability.TEXT_STYLE in capabilities or Capability.TEXT in capabilities


def full_size_single_line(rich: RichText) -> RichText:
    """A label with one line shows it at the label's size.

    A modifier-only control's only line is a modifier line (0.85em); written
    inline, that relative size would be lost when the fitted size moves onto
    the block, so the label would render larger than it was measured.
    """
    if len(rich.lines) != 1 or all(run.size_em is None for run in rich.lines[0]):
        return rich
    return RichText((tuple(Run(r.text, r.colour, r.bold) for r in rich.lines[0]),))


def _write_rich(job: RenderJob, slot: Slot, rich: RichText, frames: list[Rect]) -> None:
    rich = full_size_single_line(rich)
    fit = fit_for_slot(job, slot, rich, frames)
    if fit is not None:
        _record_truncation(job, slot, fit, rich)
        rich = RichText(fit.lines)
    if _writes_text(job):
        for target in slot.text_targets:
            write_text_target(target, rich, fit)
    if slot.cell is not None:
        write_cell_label(slot.cell, rich, fit)


def _unchanged(fit: FitResult) -> bool:
    """The template's own size and leading on one line per line: nothing to write."""
    return (
        fit.fits
        and fit.font_size == fit.base_size
        and not fit.compact
        and len(fit.wrapped) == len(fit.lines)
    )


def write_plain_fit(job: RenderJob, slot: Slot, frames: list[Rect]) -> FitResult | None:
    """ "Auto" for a label without modifier lines: size it, keep its text and markup.

    The foreignObject keeps its markup and only takes the size (Chromium wraps
    it at the same width the fit measured); the ``<text>`` fallback gets the
    wrapped lines as tspans; the model cell gets ``fontSize``. Plain text is
    never shortened: a label that is too long even at the minimum is written
    at the minimum and reported in ``RenderReport.text_overflow``.
    """
    rich = slot_plain_text(slot)
    if rich is None:
        return None
    fit = fit_for_slot(job, slot, rich, frames, plain=True)
    if fit is None:
        return None
    if not fit.fits:
        record_text_overflow(job, slot, rich.plain(" "))
    if _unchanged(fit):
        return fit
    if _writes_text(job):
        for target in slot.text_targets:
            if target.kind is TextTargetKind.FOREIGN_OBJECT:
                apply_fit_to_div(target.element, fit, every_descendant=True)
            else:
                write_text_element(target.element, RichText(fit.lines), fit)
    if slot.cell is not None:
        fit_cell_label(slot.cell, fit)
    return fit


def _colour_modifier_box(job: RenderJob, slot: Slot) -> None:
    assert job.slots is not None
    if not job.ctx.colour_modifiers or slot.role not in BOX_SLOT_ROLES:
        return
    if slot.input_key is None or slot.modifier_index is None:
        return
    modifier = job.resolver.modifier_for(slot.input_key, slot.modifier_index)
    colour = job.resolver.modifier_box_colour(modifier) if modifier else None
    if colour is None:
        return
    box = BoxStyle(stroke=colour)
    if Capability.SHAPE_STYLE in job.slots.capabilities and slot.shape is not None:
        style_shape(slot.shape, box)
    if slot.cell is not None:
        style_cell_box(slot.cell, box)


def apply_modifier_presentation(job: RenderJob) -> None:
    """Style hook: rich modifier text, text fit and modifier-box colours.

    Single-token slots with modifier lines get rich text (fitted unless the
    role says ``fit="none"``); under "Auto" every other label is fitted too.
    """
    if job.slots is None:
        return
    frames: list[Rect] | None = None  # painted shapes, scanned on first use
    auto = job.ctx.theme is not None
    for slot in job.slots.slots:
        single = len(slot.tokens) == 1
        rich = (
            job.resolver.rich_for(slot.key, _overflow_for(job, slot))
            if single
            else None
        )
        if rich is not None and not rich.is_plain:
            if frames is None:
                frames = painted_frames(job.doc.root) if job.doc is not None else []
            _write_rich(job, slot, rich, frames)
        elif auto and is_auto(job, slot):
            if frames is None:
                frames = painted_frames(job.doc.root) if job.doc is not None else []
            write_plain_fit(job, slot, frames)
        if single:
            _colour_modifier_box(job, slot)
    job.write_model()


__all__ = [
    "apply_fit_to_div",
    "apply_modifier_presentation",
    "content_host",
    "css_px",
    "fit_cell_label",
    "fit_for_slot",
    "foreign_box_width",
    "foreign_font",
    "label_centre",
    "painted_frames",
    "record_text_overflow",
    "rich_html",
    "slot_fit_box",
    "strip_label_font_sizes",
    "visible_frame",
    "write_cell_label",
    "write_foreign_object",
    "write_plain_fit",
    "write_text_element",
]

if __name__ == "__main__":
    pass
