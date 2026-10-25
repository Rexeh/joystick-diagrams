"""Theme model, built-in styles and the active-style setting (plan §3).

A ``Theme`` is a sparse set of styling decisions: every field is nullable and
``None`` means "leave the template's own value alone" (adjust mode). Themes are
layered field by field with ``merge_themes`` so a user copy only needs to hold
what it changes. Author defaults stored inside a template are out of scope for
the proof of concept; ``resolve_theme`` takes an ``author`` layer so they can be
added without changing callers.

"Original (unchanged)" is a sentinel id (``TEMPLATE_ORIGINAL_THEME_ID``). It is
never a ``Theme`` instance: ``RenderContext.theme`` is ``None`` and the legacy
regex engine renders, byte-identical to before. The user-facing name is always
``ORIGINAL_THEME_NAME``; the internal id never appears in the UI.

Persistence (user copies) lives in ``db/db_themes.py`` and
``db/theme_service.py``; everything here is pure data so it can run on a render
worker.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from enum import Enum
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from joystick_diagrams.db import db_settings

_logger = logging.getLogger(__name__)

# ── Settings ───────────────────────────────────────────────────────────

ACTIVE_THEME_SETTING_KEY = "active_theme_id"

TEMPLATE_ORIGINAL_THEME_ID = "template_original"
ORIGINAL_THEME_NAME = "Original (unchanged)"

THEME_SCHEMA_VERSION = 1

Colour = Annotated[
    str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$")
]


# ── Model ──────────────────────────────────────────────────────────────


class _Sparse(BaseModel):
    """Base for the nullable style records; unknown keys are ignored on load."""

    model_config = ConfigDict(validate_assignment=True, extra="ignore")

    def is_empty(self) -> bool:
        return all(value is None for value in self.__dict__.values())


class TextStyle(_Sparse):
    font_family: str | None = None  # family name; see ``font_stack``
    font_size: float | None = None  # px
    font_weight: Literal["normal", "bold"] | None = None
    font_style: Literal["normal", "italic"] | None = None
    colour: Colour | None = None
    # Shrink-to-fit of multi-line labels (render/text_fit.py, spike S5).
    # ``None`` means "shrink" down to ``min_font_size`` (default 6.5px).
    fit: Literal["none", "shrink"] | None = None
    min_font_size: float | None = None  # px


class BoxStyle(_Sparse):
    fill: Colour | None = None
    stroke: Colour | None = None
    stroke_width: float | None = None
    corner_radius: float | None = None


class LineStyle(_Sparse):
    stroke: Colour | None = None
    stroke_width: float | None = None


class RoleStyle(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="ignore")

    text: TextStyle = Field(default_factory=TextStyle)
    box: BoxStyle = Field(default_factory=BoxStyle)


class ThemeRole(str, Enum):
    """Styling roles. Distinct from the structural ``render.slots.SlotRole``."""

    BOUND = "BOUND"  # a control with a binding
    UNBOUND = "UNBOUND"  # a control (or modifier box) that stays empty
    MODIFIER = "MODIFIER"  # modifier boxes and modifier lines
    TITLE = "TITLE"  # TEMPLATE_NAME
    DATE = "DATE"  # CURRENT_DATE


class Theme(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="ignore")

    schema_version: int = THEME_SCHEMA_VERSION
    theme_id: str
    name: str
    based_on: str | None = None  # built-in id a user copy was made from
    roles: dict[ThemeRole, RoleStyle] = Field(default_factory=dict)
    leader_line: LineStyle = Field(default_factory=LineStyle)

    def role(self, role: ThemeRole) -> RoleStyle:
        """The style for ``role``; an empty ``RoleStyle`` when the theme sets nothing."""
        return self.roles.get(ThemeRole(role)) or RoleStyle()

    def text(self, role: ThemeRole) -> TextStyle:
        return self.role(role).text

    def box(self, role: ThemeRole) -> BoxStyle:
        return self.role(role).box


# ── Layering ───────────────────────────────────────────────────────────


def _merge_sparse(base: BaseModel, over: BaseModel) -> BaseModel:
    """Field-by-field merge: a non-``None`` value in ``over`` wins."""
    merged = {}
    for name in type(base).model_fields:
        base_value = getattr(base, name)
        over_value = getattr(over, name)
        if isinstance(base_value, BaseModel) and isinstance(over_value, BaseModel):
            merged[name] = _merge_sparse(base_value, over_value)
        else:
            merged[name] = base_value if over_value is None else over_value
    return type(base)(**merged)


def merge_themes(*layers: Theme | None) -> Theme | None:
    """Merge themes bottom-up: later layers override earlier ones field by field.

    Identity fields (``theme_id``, ``name``, ``based_on``) come from the topmost
    layer. Returns ``None`` when every layer is ``None``.
    """
    present = [layer for layer in layers if layer is not None]
    if not present:
        return None
    result = present[0]
    for layer in present[1:]:
        roles: dict[ThemeRole, RoleStyle] = dict(result.roles)
        for role, style in layer.roles.items():
            below = roles.get(role)
            roles[role] = (
                style if below is None else _merge_sparse(below, style)  # type: ignore[assignment]
            )
        result = Theme(
            theme_id=layer.theme_id,
            name=layer.name,
            based_on=layer.based_on,
            roles=roles,
            leader_line=_merge_sparse(result.leader_line, layer.leader_line),  # type: ignore[arg-type]
        )
    return result


def resolve_theme(theme: Theme | None, author: Theme | None = None) -> Theme | None:
    """The theme the style writer sees: ``author`` defaults under the chosen theme.

    ``author`` is the hook for template-embedded defaults (plan §3.4); nothing
    sets it yet. ``None`` means Original (unchanged): nothing is written.
    """
    if theme is None:
        return None
    return merge_themes(author, theme)


# ── Fonts (POC: no downloads, no bundling) ─────────────────────────────


class FontChoice(BaseModel):
    """A family offered in the style editor. ``ofl`` marks fonts that are only
    offered when installed (checked by the UI through ``QFontDatabase``)."""

    model_config = ConfigDict(frozen=True)

    family: str
    stack: str  # CSS font-family value with fallbacks
    ofl: bool = False


FONT_CHOICES: tuple[FontChoice, ...] = (
    FontChoice(family="Helvetica", stack="Helvetica, Arial, sans-serif"),
    FontChoice(family="Arial", stack="Arial, Helvetica, sans-serif"),
    FontChoice(family="Verdana", stack="Verdana, Geneva, sans-serif"),
    FontChoice(family="Tahoma", stack="Tahoma, Geneva, sans-serif"),
    FontChoice(family="Trebuchet MS", stack='"Trebuchet MS", Helvetica, sans-serif'),
    FontChoice(family="Georgia", stack='Georgia, "Times New Roman", serif'),
    FontChoice(family="Courier New", stack='"Courier New", Courier, monospace'),
    # OFL-licensed families commonly present on Linux/Windows installs. They are
    # not bundled or embedded (gap: fonts reach PNG/PDF only when installed).
    FontChoice(family="Noto Sans", stack='"Noto Sans", Arial, sans-serif', ofl=True),
    FontChoice(
        family="Liberation Sans", stack='"Liberation Sans", Arial, sans-serif', ofl=True
    ),
    FontChoice(
        family="Liberation Sans Narrow",
        stack='"Liberation Sans Narrow", "Arial Narrow", Arial, sans-serif',
        ofl=True,
    ),
    FontChoice(
        family="Liberation Mono",
        stack='"Liberation Mono", "Courier New", monospace',
        ofl=True,
    ),
    FontChoice(
        family="Atkinson Hyperlegible",
        stack='"Atkinson Hyperlegible", Arial, sans-serif',
        ofl=True,
    ),
    FontChoice(family="Barlow", stack="Barlow, Arial, sans-serif", ofl=True),
    FontChoice(
        family="Barlow Condensed",
        stack='"Barlow Condensed", "Arial Narrow", Arial, sans-serif',
        ofl=True,
    ),
)

_FONT_STACKS: MappingProxyType[str, str] = MappingProxyType(
    {choice.family.casefold(): choice.stack for choice in FONT_CHOICES}
)


def font_stack(family: str) -> str:
    """CSS ``font-family`` value for a family name (quoted with a sans-serif fallback)."""
    known = _FONT_STACKS.get(family.strip().casefold())
    if known is not None:
        return known
    name = family.strip()
    quoted = f'"{name}"' if " " in name else name
    return f"{quoted}, sans-serif"


# ── Built-in styles ────────────────────────────────────────────────────


def _role(text: dict | None = None, box: dict | None = None) -> RoleStyle:
    return RoleStyle(text=TextStyle(**(text or {})), box=BoxStyle(**(box or {})))


CLEAN_THEME = Theme(
    theme_id="clean",
    name="Clean",
    roles={
        ThemeRole.BOUND: _role(
            {"colour": "#111827"},
            {"stroke": "#374151", "stroke_width": 1.5, "corner_radius": 4},
        ),
        ThemeRole.UNBOUND: _role(
            {"colour": "#9CA3AF"},
            {"stroke": "#D1D5DB", "stroke_width": 1, "corner_radius": 4},
        ),
        ThemeRole.MODIFIER: _role(
            {"colour": "#374151"},
            {"stroke": "#6B7280", "stroke_width": 1.5, "corner_radius": 4},
        ),
        ThemeRole.TITLE: _role({"colour": "#111827", "font_weight": "bold"}),
        ThemeRole.DATE: _role({"colour": "#6B7280"}),
    },
    leader_line=LineStyle(stroke="#6B7280", stroke_width=1.5),
)

_PRINT_TEXT = {"font_family": "Arial", "colour": "#000000"}
PRINT_FRIENDLY_THEME = Theme(
    theme_id="print_friendly",
    name="Print friendly",
    roles={
        ThemeRole.BOUND: _role(
            _PRINT_TEXT, {"stroke": "#000000", "stroke_width": 1.5, "fill": "#FFFFFF"}
        ),
        ThemeRole.UNBOUND: _role(
            {"font_family": "Arial", "colour": "#6B6B6B"},
            {"stroke": "#9E9E9E", "stroke_width": 1, "fill": "#FFFFFF"},
        ),
        ThemeRole.MODIFIER: _role(
            {**_PRINT_TEXT, "font_style": "italic"},
            {"stroke": "#000000", "stroke_width": 1, "fill": "#FFFFFF"},
        ),
        ThemeRole.TITLE: _role({**_PRINT_TEXT, "font_weight": "bold"}),
        ThemeRole.DATE: _role(_PRINT_TEXT),
    },
    leader_line=LineStyle(stroke="#000000", stroke_width=1.5),
)

_HC_TEXT = {"font_family": "Arial", "colour": "#000000", "font_weight": "bold"}
HIGH_CONTRAST_THEME = Theme(
    theme_id="high_contrast",
    name="High contrast",
    roles={
        ThemeRole.BOUND: _role(
            _HC_TEXT,
            {
                "stroke": "#000000",
                "stroke_width": 2.5,
                "fill": "#FFFFFF",
                "corner_radius": 0,
            },
        ),
        ThemeRole.UNBOUND: _role(
            {"font_family": "Arial", "colour": "#555555", "font_weight": "normal"},
            {
                "stroke": "#888888",
                "stroke_width": 1.5,
                "fill": "#EEEEEE",
                "corner_radius": 0,
            },
        ),
        ThemeRole.MODIFIER: _role(
            _HC_TEXT,
            {
                "stroke": "#000000",
                "stroke_width": 2,
                "fill": "#FFFFFF",
                "corner_radius": 0,
            },
        ),
        ThemeRole.TITLE: _role(_HC_TEXT),
        ThemeRole.DATE: _role(_HC_TEXT),
    },
    leader_line=LineStyle(stroke="#000000", stroke_width=2.5),
)

BUILTIN_THEMES: MappingProxyType[str, Theme] = MappingProxyType(
    {
        theme.theme_id: theme
        for theme in (CLEAN_THEME, PRINT_FRIENDLY_THEME, HIGH_CONTRAST_THEME)
    }
)


def is_builtin_theme_id(theme_id: str | None) -> bool:
    return theme_id in BUILTIN_THEMES


def is_original_theme_id(theme_id: str | None) -> bool:
    return not theme_id or theme_id == TEMPLATE_ORIGINAL_THEME_ID


def builtin_theme(theme_id: str | None) -> Theme | None:
    """A built-in by id; ``None`` for Original, unknown ids and user ids."""
    return BUILTIN_THEMES.get(theme_id or "")


def theme_display_name(theme_id: str | None, themes: Iterable[Theme] = ()) -> str:
    """User-facing name for an id: Original for the sentinel/unknown ids."""
    if is_original_theme_id(theme_id):
        return ORIGINAL_THEME_NAME
    for theme in themes:
        if theme.theme_id == theme_id:
            return theme.name
    builtin = builtin_theme(theme_id)
    return builtin.name if builtin else ORIGINAL_THEME_NAME


# ── Active style setting (read at call time) ──────────────────────────


def get_active_theme_id() -> str:
    """The stored active style id; missing or blank means Original."""
    raw = db_settings.get_setting(ACTIVE_THEME_SETTING_KEY)
    return raw.strip() if raw and raw.strip() else TEMPLATE_ORIGINAL_THEME_ID


def set_active_theme_id(theme_id: str | None) -> None:
    db_settings.add_update_setting_value(
        ACTIVE_THEME_SETTING_KEY, theme_id or TEMPLATE_ORIGINAL_THEME_ID
    )


if __name__ == "__main__":
    pass
