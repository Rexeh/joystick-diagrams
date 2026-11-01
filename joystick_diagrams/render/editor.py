"""Rendering for the layout editor screen (plan §5.2): ``render_for_editor``.

The editor needs the same picture the export produces, plus the structure to
hit-test it: every slot's identity and geometry, which ones can move or resize,
how leader lines attach, and what did not fit. ``render_for_editor`` runs the
normal DOM pipeline with ``RenderContext.preview=True`` so the SVG carries
``data-jd-slot`` / ``data-jd-role`` / ``data-jd-added`` / ``data-jd-edge``
attributes (see ``layout_apply``), and returns an ``EditorRender``.

How E2 uses it::

    layers = AppState().layout_service.get_layers(
        template.template_key, wrapper.profile_key, device_guid=export_device.device_id
    )
    render = render_for_editor(template, export_device, layers=layers)
    # or, template only (no device bound yet): tokens stay visible as placeholders
    render = render_for_editor(template, None, layers=layers)
    # options: EditorOptions(ctx=..., binding=..., profile_name="DCS", annotate=True)

    render.svg_text  # serve at jdeditor://app/template.svg
    render.slots  # list[LayoutSlotInfo]: target, bbox (after ops), movable, resizable, hidden, edges, layer, added_uid …
    render.edges  # list[LayoutEdgeInfo]: edge_id, points, source/target slot and attachment kind
    render.notices  # list[LayoutNotice]: slot_missing, resize_refused, template_updated, box_unplaced, layout_unsupported …
    render.supported  # False → show the "Moving boxes isn't available for this template" banner
    render.overflow  # {"BUTTON_1": 2}: modifiers with no box (the "+N more" badge)
    render.as_dict()  # JSON-ready payload for the QWebChannel ``stateChanged``/``templateChanged`` signals

Then, on a drop, the editor builds an op (``render/layout.py``), persists it with
``layout_service.append_op(...)`` and calls ``render_for_editor`` again with the
refreshed layers (debounced; the whole call is ~25 ms on the largest template).

Without a device the ``PlaceholderResolver`` leaves every token in place (upper
case) so the user sees ``BUTTON_1`` labels; ``modifier_count`` is 0, so dynamic
``add_modifier_boxes`` ops with ``count="auto"`` add nothing until a profile is
chosen (explicit counts still render).
"""

from __future__ import annotations

import dataclasses
import html
from dataclasses import asdict, dataclass, field
from typing import Any

from joystick_diagrams.render.binding import BindingOptions, BindingResolver
from joystick_diagrams.render.context import (
    RenderContext,
    RenderFallbackError,
    RenderReport,
)
from joystick_diagrams.render.layout import LayoutLayers
from joystick_diagrams.render.layout_apply import (
    LayoutEdgeInfo,
    LayoutNotice,
    LayoutResult,
    LayoutSlotInfo,
)
from joystick_diagrams.render.pipeline import RenderJob, run_pipeline
from joystick_diagrams.render.slots import Rect
from joystick_diagrams.render.tokens import classify


class PlaceholderResolver:
    """A resolver that keeps tokens visible (template-only preview, no device)."""

    def __init__(self, profile_name: str = "") -> None:
        self.profile_name = profile_name

    def text_for(self, token: str) -> str:
        info = classify(token)
        if info.role.value == "title" and self.profile_name:
            return self.profile_name
        return token.upper()

    def html_for(self, token: str) -> str:
        return html.escape(self.text_for(token), quote=False)

    def rich_for(self, token: str, overflow: int = 0):
        return None

    def input_keys(self) -> list[str]:
        return []

    def modifier_count(self, input_key: str) -> int:
        return 0

    def modifier_for(self, input_key: str, index: int):
        return None

    def modifier_box_colour(self, modifier):
        return None

    def resolve_label(self, command: str) -> str:
        return command


@dataclass(frozen=True)
class EditorRender:
    svg_text: str
    supported: bool
    page: Rect | None
    slots: list[LayoutSlotInfo] = field(default_factory=list)
    edges: list[LayoutEdgeInfo] = field(default_factory=list)
    notices: list[LayoutNotice] = field(default_factory=list)
    skipped_ops: tuple[str, ...] = ()
    unplaced: list[Any] = field(default_factory=list)
    overflow: dict[str, int] = field(default_factory=dict)
    report: RenderReport | None = None

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready structure (``Rect`` → ``{x, y, width, height}``) for the bridge."""
        return {
            "supported": self.supported,
            "page": asdict(self.page) if self.page is not None else None,
            "slots": [_jsonable(asdict(slot)) for slot in self.slots],
            "edges": [_jsonable(asdict(edge)) for edge in self.edges],
            "notices": [asdict(notice) for notice in self.notices],
            "skippedOps": list(self.skipped_ops),
            "unplaced": [asdict(item) for item in self.unplaced],
            "overflow": dict(self.overflow),
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def default_editor_options(ctx: RenderContext) -> BindingOptions:
    from joystick_diagrams.export import dom_binding_options

    return dom_binding_options(ctx)


def _resolver(export_device: Any, profile_name: str, options: BindingOptions):
    if export_device is None:
        return PlaceholderResolver(profile_name)
    wrapper = getattr(export_device, "profile_wrapper", None)
    name = getattr(wrapper, "profile_name", None) or profile_name
    return BindingResolver(
        device=export_device.device, profile_name=name, options=options
    )


def _from_result(
    outcome_text: str, result: LayoutResult | None, job: RenderJob
) -> EditorRender:
    report = job.report()
    if result is None:
        return EditorRender(outcome_text, supported=False, page=None, report=report)
    return EditorRender(
        svg_text=outcome_text,
        supported=result.supported,
        page=result.page,
        slots=list(result.slots),
        edges=list(result.edges),
        notices=list(result.notices),
        skipped_ops=tuple(result.skipped_ops),
        unplaced=list(result.unplaced),
        overflow=dict(job.overflow),
        report=report,
    )


@dataclass(frozen=True)
class EditorOptions:
    """Knobs for ``render_for_editor`` (all optional)."""

    ctx: RenderContext | None = (
        None  # default: build_render_context() under an AppState
    )
    binding: BindingOptions | None = None  # default: dom_binding_options(ctx)
    profile_name: str = "Preview"  # TEMPLATE_NAME text when no device is bound
    annotate: bool = True  # data-jd-* attributes for the overlay


def render_for_editor(
    template: Any,
    export_device: Any = None,
    *,
    layers: LayoutLayers | None = None,
    options: EditorOptions | None = None,
) -> EditorRender:
    """Render ``template`` for the editor, with or without a bound device.

    ``template`` is a ``Template`` (``raw_data``, ``template_key``,
    ``content_hash``); ``export_device`` an ``ExportDevice`` or ``None``;
    ``layers`` the ``LayoutLayers`` to apply (default: the ones in ``ctx.layouts``
    for this template and profile, else none). Falls back to the untouched
    template text with ``supported=False`` when the file isn't draw.io.
    """
    options = options or EditorOptions()
    ctx = dataclasses.replace(
        options.ctx or _default_context(),
        preview=options.annotate,
        engine_override="dom",
    )
    binding = options.binding or default_editor_options(ctx)
    resolver = _resolver(export_device, options.profile_name, binding)
    wrapper = getattr(export_device, "profile_wrapper", None)
    job = RenderJob(
        raw=template.raw_data,
        ctx=ctx,
        resolver=resolver,
        hooks=_hooks(),
        template_key=getattr(template, "template_key", None),
        device_guid=getattr(export_device, "device_id", None),
        profile_key=getattr(wrapper, "profile_key", None),
        content_hash=_content_hash(template),
        layers=layers,
        describe_layout=True,
    )
    try:
        outcome = run_pipeline(job)
    except RenderFallbackError as error:
        job.notices.append(error.notice)
        job.details.append(error.detail)
        render = _from_result(template.raw_data, None, job)
        render.notices.append(LayoutNotice("layout_unsupported", detail=error.detail))
        return render
    return _from_result(outcome.svg_text, job.layout, job)


def _hooks():
    from joystick_diagrams.render import default_hooks

    return default_hooks()


def _default_context() -> RenderContext:
    from joystick_diagrams.app_state import AppState
    from joystick_diagrams.render.context import build_render_context

    if AppState._inst is not None:
        return build_render_context()
    return RenderContext()


def _content_hash(template: Any) -> str | None:
    try:
        return getattr(template, "content_hash", None)
    except OSError:
        return None


__all__ = [
    "EditorOptions",
    "EditorRender",
    "PlaceholderResolver",
    "default_editor_options",
    "render_for_editor",
]

if __name__ == "__main__":
    pass
