"""The DOM render pipeline: ordered stages over a ``RenderJob``.

    parse → decode_model → coverage → detect/slots → layout → fill → style → serialise

Each stage is a plain callable ``(job: RenderJob) -> None``. ``layout`` and
``style`` are **extension points** for later milestones: they run every hook in
``PipelineHooks.layout`` / ``PipelineHooks.style`` and do nothing by default.

Contract for hook authors
-------------------------
- ``job.doc.root`` is the lxml root of the rendered SVG; ``job.model`` the
  decoded draw.io model. Both may be mutated. The pipeline writes the model back
  into ``content=`` **after** fill, and ``style`` runs after that; a style hook
  that edits model cells must therefore call ``job.write_model()`` itself (or
  ``stage_fill`` could be reordered in a custom stage list).
- ``job.slots`` (``SlotMap``) says what is known: only touch shapes/edges/
  geometry when the matching ``Capability`` is present.
- ``job.resolver`` answers ``text_for(token)`` so a hook can rebuild rich runs
  (e.g. coloured modifier keys) from the same text the fill used.
- Layout hooks run **before** fill so they see original tokens; style hooks run
  after fill so they see final text.
- Raise ``RenderFallbackError`` to hand the render to the legacy engine; any other
  exception is logged with a traceback by the caller and also falls back.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from lxml import etree

from joystick_diagrams.render.adapters import detect_adapter
from joystick_diagrams.render.binding import BindingResolver, fill_node_text, fill_text
from joystick_diagrams.render.context import (
    Engine,
    RenderContext,
    RenderFallbackError,
    RenderNotice,
    RenderOutcome,
    RenderReport,
)
from joystick_diagrams.render.coverage import coverage_mismatch
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel, ModelDecodeError
from joystick_diagrams.render.slots import Capability, SlotMap
from joystick_diagrams.render.tokens import BLANK_RE

Stage = Callable[["RenderJob"], None]
Hook = Callable[["RenderJob"], None]


@dataclass
class PipelineHooks:
    layout: Sequence[Hook] = ()
    style: Sequence[Hook] = ()


@dataclass
class RenderJob:
    raw: str
    ctx: RenderContext
    resolver: BindingResolver
    hooks: PipelineHooks = field(default_factory=PipelineHooks)
    doc: TemplateDocument | None = None  # pre-parsed pristine copy may be injected
    model: DrawioModel | None = None
    slots: SlotMap | None = None
    notices: list[RenderNotice] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    overflow: dict[str, int] = field(default_factory=dict)
    output: str | None = None
    # Identity of what is rendered, for layout lookups (None when unknown/mocked).
    template_key: str | None = None
    profile_key: str | None = None
    content_hash: str | None = None
    layers: Any = None  # explicit LayoutLayers; None → ctx.layers_for(...)
    layout: Any = None  # LayoutResult filled by the layout hook
    describe_layout: bool = False  # run the layout stage even without ops (editor)
    skipped_ops: list[str] = field(default_factory=list)

    def write_model(self) -> None:
        """Serialise the (edited) model back into the root ``content`` attribute."""
        if self.doc is not None and self.model is not None:
            self.doc.root.set("content", self.model.to_content())

    def report(self) -> RenderReport:
        return RenderReport(
            engine=Engine.DOM,
            adapter=self.slots.adapter if self.slots else None,
            capabilities=self.slots.capabilities if self.slots else frozenset(),
            notices=tuple(self.notices),
            details=tuple(self.details),
            overflow=MappingProxyType(dict(self.overflow)),
            skipped_ops=tuple(self.skipped_ops),
        )


# ── Stages ──


def stage_parse(job: RenderJob) -> None:
    if job.doc is not None:
        return
    try:
        job.doc = TemplateDocument.parse(job.raw)
    except (etree.XMLSyntaxError, ValueError) as e:
        raise RenderFallbackError(RenderNotice.PARSE_ERROR, str(e)) from e


def stage_decode_model(job: RenderJob) -> None:
    assert job.doc is not None
    try:
        job.model = DrawioModel.from_content(job.doc.root.get("content"))
    except ModelDecodeError as e:
        raise RenderFallbackError(RenderNotice.NOT_DRAWIO, str(e)) from e


def stage_coverage(job: RenderJob) -> None:
    assert job.doc is not None
    reason = coverage_mismatch(job.doc)
    if reason is not None:
        raise RenderFallbackError(RenderNotice.COVERAGE_MISMATCH, reason)


def record_overflow(job: RenderJob) -> None:
    """(Re)compute ``job.overflow``: bound modifiers minus template boxes per input."""
    assert job.slots is not None
    job.overflow.clear()
    for input_key in job.resolver.input_keys():
        boxes = job.slots.modifier_box_count(input_key)
        bound = job.resolver.modifier_count(input_key)
        if boxes and bound > boxes:
            job.overflow[input_key.upper()] = bound - boxes


def stage_detect(job: RenderJob) -> None:
    assert job.doc is not None and job.model is not None
    adapter = detect_adapter(job.doc, job.model)
    job.slots = adapter.build_slots(job.doc, job.model)
    job.details.extend(job.slots.notices)
    if Capability.SHAPE_STYLE not in job.slots.capabilities:
        job.notices.append(RenderNotice.ALIGNMENT_DEGRADED)
    record_overflow(job)


def stage_layout(job: RenderJob) -> None:
    """Extension point: layout ops (move/resize/hide/add boxes).

    ``default_hooks()`` installs ``layout_apply.apply_layout`` here; a job without
    hooks leaves the document untouched.
    """
    for hook in job.hooks.layout:
        hook(job)


def _fill_body(job: RenderJob) -> None:
    assert job.doc is not None
    resolve = job.resolver.text_for
    for node in job.doc.root.iter():
        if isinstance(node.tag, str):
            fill_node_text(node, resolve)
        elif node.tail and BLANK_RE.search(node.tail):
            node.tail = fill_text(node.tail, resolve)


def _fill_model(job: RenderJob) -> None:
    assert job.model is not None
    for cell in job.model.cells():
        resolve = job.resolver.html_for if cell.is_html else job.resolver.text_for
        label = cell.label
        if BLANK_RE.search(label):
            cell.set_label(fill_text(label, resolve))
        tooltip = cell.tooltip
        if tooltip and BLANK_RE.search(tooltip):
            cell.set_tooltip(fill_text(tooltip, resolve))


def stage_fill(job: RenderJob) -> None:
    _fill_body(job)
    _fill_model(job)
    job.write_model()


def stage_style(job: RenderJob) -> None:
    """Extension point: theme writer and modifier colouring. No-op by default."""
    for hook in job.hooks.style:
        hook(job)


def stage_serialise(job: RenderJob) -> None:
    assert job.doc is not None
    job.output = job.doc.serialise()


DEFAULT_STAGES: tuple[Stage, ...] = (
    stage_parse,
    stage_decode_model,
    stage_coverage,
    stage_detect,
    stage_layout,
    stage_fill,
    stage_style,
    stage_serialise,
)


def run_pipeline(
    job: RenderJob, stages: Sequence[Stage] = DEFAULT_STAGES
) -> RenderOutcome:
    for stage in stages:
        stage(job)
    assert job.output is not None
    return RenderOutcome(job.output, job.report())


if __name__ == "__main__":
    pass
