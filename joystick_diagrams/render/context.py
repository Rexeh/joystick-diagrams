"""Render context, engine choice and the outcome/report types (plan §1.4–§1.5).

``RenderContext`` is an immutable snapshot built on the *calling* thread (UI)
before an export batch starts; the worker never reads services or the database
for anything the context carries: the resolved theme, the modifier key registry
snapshot (with its colouring/sides/key-display flags), the "Showing modifiers"
choice, the custom-label snapshot and the layout documents
(``layouts[(template_key, profile_key)]`` with ``profile_key == ""`` for the
template layer; see ``render/layout.py``). ``layers_for`` resolves the two
layers one render needs; ``preview=True`` asks the layout stage to annotate the
SVG with ``data-jd-*`` attributes for the editor overlay.

``choose_engine`` implements the decision-5 guarantee: the legacy regex engine
runs unless the user has opted into something that needs the DOM engine (a
style other than Original, modifier colouring, "Add them under the main text",
simplified key names, layout ops), or the hidden ``render_engine`` setting
forces one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any

from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    ModifierKeyDisplay,
    ModifierRegistrySnapshot,
    get_modifier_display,
    get_modifier_key_display,
    modifier_colouring_enabled,
    modifier_sides_merged,
)
from joystick_diagrams.render.slots import Capability
from joystick_diagrams.render.theme import (
    Theme,
    builtin_theme,
    get_active_theme_id,
    resolve_theme,
)

RENDER_ENGINE_SETTING_KEY = "render_engine"  # hidden: "legacy" | "dom" | unset


class Engine(str, Enum):
    LEGACY = "legacy"
    DOM = "dom"


class RenderNotice(str, Enum):
    """Reason codes; user-facing wording belongs to ``ui/strings.py`` (plan §5.5.9)."""

    PARSE_ERROR = "parse_error"  # not XML / entity namespace / invalid
    NOT_DRAWIO = "not_drawio"  # valid XML but no decodable draw.io model
    COVERAGE_MISMATCH = "coverage_mismatch"  # tokens outside text nodes
    UNEXPECTED_ERROR = "unexpected_error"
    FELL_BACK_TO_LEGACY = "fell_back_to_legacy"
    ALIGNMENT_DEGRADED = "alignment_degraded"  # text only, no shapes/edges/layout
    LAYOUT_UNSUPPORTED = "layout_unsupported"  # layout ops refused for this template
    LAYOUT_OPS_SKIPPED = "layout_ops_skipped"  # some ops no longer fit (see details)
    TEMPLATE_UPDATED = "template_updated"  # ops were saved against other bytes
    BOXES_UNPLACED = "boxes_unplaced"  # auto-add found no room for some boxes


class RenderFallbackError(Exception):
    """Raised by the DOM engine when the legacy engine must render instead."""

    def __init__(self, notice: RenderNotice, detail: str = "") -> None:
        super().__init__(detail or notice.value)
        self.notice = notice
        self.detail = detail


_EMPTY_MAP: Mapping[Any, Any] = MappingProxyType({})


def _as_document(value: Any, template_key: str, profile_key: str):
    """Accept a ``LayoutDocument``, a list of ops/dicts or ``None`` (tests pass lists)."""
    from joystick_diagrams.render.layout import LayoutDocument

    if value is None:
        return LayoutDocument(template_key=template_key, profile_key=profile_key)
    if isinstance(value, LayoutDocument):
        return value
    ops = [op for op in value if not isinstance(op, str)]
    return LayoutDocument(template_key=template_key, profile_key=profile_key, ops=ops)


@dataclass(frozen=True)
class RenderContext:
    theme: Theme | None = None  # resolved theme; None → Original (unchanged)
    colour_modifiers: bool = False  # "Colour by modifier key" master toggle
    registry: ModifierRegistrySnapshot | None = (
        None  # modifier key registry; None → seeds, colouring off
    )
    modifier_display: ModifierDisplay = ModifierDisplay.TEMPLATE_BOXES
    layouts: Mapping[tuple[str, str], Any] = (
        _EMPTY_MAP  # (template_key, profile_key) -> LayoutDocument; "" = template layer
    )
    labels: Mapping[str, str] | None = (
        None  # snapshot of custom labels; None → no resolution
    )
    engine_override: str | None = None  # RENDER_ENGINE_SETTING_KEY value
    now: datetime | None = None  # frozen date for tests; None → datetime.now()
    preview: bool = False

    @property
    def simplified_key_names(self) -> bool:
        """ "Show key names: Simplified" is applied by the DOM resolver only (POC)."""
        return (
            self.registry is not None
            and self.registry.key_display is ModifierKeyDisplay.SIMPLIFIED
        )

    def layers_for(self, template_key: str | None, profile_key: str | None):
        """``LayoutLayers`` (template layer then profile layer) for one render."""
        from joystick_diagrams.render.layout import LayoutDocument, LayoutLayers

        if template_key is None:
            return LayoutLayers()
        template = self.layouts.get((template_key, ""))
        profile = self.layouts.get((template_key, profile_key)) if profile_key else None
        return (
            LayoutLayers(
                _as_document(template, template_key, ""),
                _as_document(profile, template_key, profile_key or ""),
            )
            if (template is not None or profile is not None)
            else LayoutLayers(
                LayoutDocument(template_key=template_key),
                LayoutDocument(template_key=template_key),
            )
        )

    def has_layout_ops(self, template_key: str | None, profile_key: str | None) -> bool:
        """Whether either layer for this diagram holds ops (duck-typed for tests)."""
        if template_key is None:
            return False
        for key in ((template_key, profile_key or ""), (template_key, "")):
            value = self.layouts.get(key)
            if value is None:
                continue
            if not (
                getattr(value, "is_empty", False)
                if hasattr(value, "ops")
                else not value
            ):
                return True
        return False


@dataclass(frozen=True)
class RenderReport:
    engine: Engine
    adapter: str | None = None
    capabilities: frozenset[Capability] = frozenset()
    notices: tuple[RenderNotice, ...] = ()
    details: tuple[str, ...] = ()
    overflow: Mapping[str, int] = field(default_factory=lambda: MappingProxyType({}))
    skipped_ops: tuple[str, ...] = ()  # uids of layout ops that could not be applied


@dataclass(frozen=True)
class RenderOutcome:
    svg_text: str
    report: RenderReport


def choose_engine(ctx: RenderContext, export_device: Any) -> Engine:
    """LEGACY unless something opted in. Duck-typed: tests use a MockTemplate."""
    if ctx.engine_override == Engine.LEGACY.value:
        return Engine.LEGACY
    if ctx.engine_override == Engine.DOM.value:
        return Engine.DOM
    template_key = getattr(
        getattr(export_device, "template", None), "template_key", None
    )
    profile_key = getattr(
        getattr(export_device, "profile_wrapper", None), "profile_key", None
    )
    opted_in = (
        ctx.theme is not None
        or ctx.colour_modifiers
        or ctx.modifier_display is ModifierDisplay.UNDER_MAIN_TEXT
        or ctx.simplified_key_names
        or ctx.has_layout_ops(template_key, profile_key)
    )
    return Engine.DOM if opted_in else Engine.LEGACY


def snapshot_labels() -> Mapping[str, str] | None:
    """Copy of the custom labels, or None when no ``AppState`` exists (tests, CLI)."""
    from joystick_diagrams.app_state import AppState

    if AppState._inst is None:
        return None
    return MappingProxyType(dict(AppState().label_service.get_all_custom_labels()))


def snapshot_registry() -> ModifierRegistrySnapshot:
    """The modifier key registry (settings read now); seeds when no ``AppState`` exists."""
    from joystick_diagrams.app_state import AppState

    if AppState._inst is not None:
        return AppState().modifier_key_service.snapshot()
    return ModifierRegistrySnapshot.default(
        sides_merged=modifier_sides_merged(),
        colouring_enabled=modifier_colouring_enabled(),
        key_display=get_modifier_key_display(),
    )


def snapshot_layouts() -> Mapping[tuple[str, str], Any]:
    """Every stored layout document; empty when no ``AppState`` exists."""
    from joystick_diagrams.app_state import AppState

    if AppState._inst is None:
        return _EMPTY_MAP
    return AppState().layout_service.snapshot()


def snapshot_theme() -> Theme | None:
    """The resolved active style; built-ins only when no ``AppState`` exists."""
    from joystick_diagrams.app_state import AppState

    if AppState._inst is not None:
        return AppState().theme_service.resolved_active()
    return resolve_theme(builtin_theme(get_active_theme_id()))


def build_render_context(now: datetime | None = None) -> RenderContext:
    """Snapshot everything the worker needs. Call on the UI thread before a batch."""
    from joystick_diagrams.db.db_settings import get_setting

    override = get_setting(RENDER_ENGINE_SETTING_KEY)
    registry = snapshot_registry()
    return RenderContext(
        theme=snapshot_theme(),
        colour_modifiers=registry.colouring_enabled,
        registry=registry,
        modifier_display=get_modifier_display(),
        layouts=snapshot_layouts(),
        labels=snapshot_labels(),
        engine_override=override.lower() if override else None,
        now=now,
    )


if __name__ == "__main__":
    pass
