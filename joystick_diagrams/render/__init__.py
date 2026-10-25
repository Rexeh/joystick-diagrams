"""DOM render engine for Joystick Diagrams templates (plan §1, §4).

Public entry points
-------------------
- ``render_device(export_device, ctx, options)`` renders one ``ExportDevice``
  with the lxml DOM engine and returns ``RenderOutcome(svg_text, report)``.
  It raises ``RenderFallbackError`` when the legacy engine must take over; the
  caller (``export.render_template``) logs and falls back.
- ``RenderContext`` / ``build_render_context`` / ``choose_engine``: the
  immutable per-batch snapshot and the engine decision (``context.py``).
- ``BindingOptions``: export-time settings shared by both engines.
- ``Slot``/``SlotMap``/``SlotRole``/``Capability``: the structural model later
  styling and layout work builds on (``slots.py``).
- ``PipelineHooks``/``RenderJob``: register layout/style stages (``pipeline.py``).
  ``default_hooks()`` installs the theme writer (``style_writer.py``), the
  modifier presentation (``modifier_presentation.py``) and the light
  ``color-scheme`` pin that every DOM render gets.
- ``Theme``/``ThemeRole``/built-ins: the style model (``theme.py``).
- Layout: ``render/layout.py`` (op model), ``layout_apply.py`` (the layout
  stage: move/resize/hide/add boxes/notes, leader-line follow, editor
  annotations), ``auto_layout.py`` (automatic modifier-box placement) and
  ``editor.py`` (``render_for_editor`` for the layout editor screen).

The legacy regex engine (``export.populate_template``) is untouched and remains
the default; see ``export.render_template`` for the dispatch.
"""

from __future__ import annotations

from typing import Any

from joystick_diagrams.render.binding import BindingOptions, BindingResolver
from joystick_diagrams.render.context import (
    RENDER_ENGINE_SETTING_KEY,
    Engine,
    RenderContext,
    RenderFallbackError,
    RenderNotice,
    RenderOutcome,
    RenderReport,
    build_render_context,
    choose_engine,
)
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.layout_apply import apply_layout
from joystick_diagrams.render.modifier_presentation import apply_modifier_presentation
from joystick_diagrams.render.pipeline import PipelineHooks, RenderJob, run_pipeline
from joystick_diagrams.render.slots import Capability, Slot, SlotMap, SlotRole
from joystick_diagrams.render.style_writer import apply_theme, pin_light_colour_scheme
from joystick_diagrams.render.theme import (
    ACTIVE_THEME_SETTING_KEY,
    BUILTIN_THEMES,
    ORIGINAL_THEME_NAME,
    TEMPLATE_ORIGINAL_THEME_ID,
    Theme,
    ThemeRole,
    resolve_theme,
)


def default_hooks() -> PipelineHooks:
    """The production stages: layout ops before fill; theme, modifier runs/colours and the pin after."""
    return PipelineHooks(
        layout=(apply_layout,),
        style=(apply_theme, apply_modifier_presentation, pin_light_colour_scheme),
    )


def render_device(
    export_device: Any,
    ctx: RenderContext,
    options: BindingOptions,
    hooks: PipelineHooks | None = None,
    document: TemplateDocument | None = None,
) -> RenderOutcome:
    """Render with the DOM engine. ``document`` may be a pristine cached parse."""
    resolver = BindingResolver(
        device=export_device.device,
        profile_name=export_device.profile_wrapper.profile_name,
        options=options,
    )
    template = export_device.template
    job = RenderJob(
        raw=template.raw_data,
        ctx=ctx,
        resolver=resolver,
        hooks=hooks if hooks is not None else default_hooks(),
        doc=document.copy() if document is not None else None,
        template_key=getattr(template, "template_key", None),
        device_guid=getattr(export_device, "device_id", None),
        profile_key=getattr(export_device.profile_wrapper, "profile_key", None),
        content_hash=_safe_content_hash(template),
    )
    return run_pipeline(job)


def _safe_content_hash(template: Any) -> str | None:
    try:
        return getattr(template, "content_hash", None)
    except OSError:  # file vanished since it was read
        return None


__all__ = [
    "ACTIVE_THEME_SETTING_KEY",
    "BUILTIN_THEMES",
    "ORIGINAL_THEME_NAME",
    "RENDER_ENGINE_SETTING_KEY",
    "TEMPLATE_ORIGINAL_THEME_ID",
    "BindingOptions",
    "BindingResolver",
    "Capability",
    "Engine",
    "PipelineHooks",
    "RenderContext",
    "RenderFallbackError",
    "RenderJob",
    "RenderNotice",
    "RenderOutcome",
    "RenderReport",
    "Slot",
    "SlotMap",
    "SlotRole",
    "TemplateDocument",
    "Theme",
    "ThemeRole",
    "build_render_context",
    "choose_engine",
    "apply_layout",
    "default_hooks",
    "render_device",
    "resolve_theme",
    "run_pipeline",
]
