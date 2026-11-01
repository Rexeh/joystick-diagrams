"""Modifier key identity: normalisation, grouping, seeds and style resolution.

Plugins emit modifier keys in each game's own vocabulary (DCS ``LShift``, Star
Citizen ``lalt``, MSFS ``BUTTON_5``, Falcon BMS ``BMS DX Shift``). This module
is the pure-logic layer that turns those raw spellings into a *canonical
identity* (for styling and priority) and a *display label* (which keeps the
side, e.g. ``"L Ctrl"``). Persistence lives in ``db/db_modifier_keys.py`` and
``db/modifier_key_service.py``; everything here works on an immutable
``ModifierRegistrySnapshot`` so it can run on a render worker.

Identity rules (plan section 2.2B):

- ``ModifierKind.QUALIFIER`` modifiers always resolve to ``(QUALIFIER, raw)``.
  They are never aliased and never coloured.
- ``ModifierKind.KEY`` modifiers look up the alias table (skipping ``side_alias``
  rows when "Treat left and right keys as the same" is off), then match group
  canonical names case-insensitively, then device-input patterns, and finally
  fall back to their own raw spelling as identity.
- Aliasing drives styling and priority only; the displayed text keeps the side.
"""

import json
import logging
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

from joystick_diagrams.db import db_settings
from joystick_diagrams.input.modifier import (
    Modifier,
    ModifierKind,
    modifier_sort_key,
    normalise_token,
    split_side,
)

_logger = logging.getLogger(__name__)

# ── Settings ───────────────────────────────────────────────────────────

MODIFIER_COLOURING_SETTING_KEY = "modifier_colouring_enabled"
MODIFIER_SIDES_MERGED_SETTING_KEY = "modifier_lr_same"
MODIFIER_KEY_DISPLAY_SETTING_KEY = "modifier_key_display"
MODIFIER_KEYS_SEED_VERSION_SETTING_KEY = "modifier_keys_seed_version"


class ModifierKeyDisplay(str, Enum):
    """How modifier key names are shown on the diagram."""

    ORIGINAL = "ORIGINAL"  # as in the game: "LShift"
    SIMPLIFIED = "SIMPLIFIED"  # registry labels: "L Shift"


DEFAULT_MODIFIER_COLOURING = False
DEFAULT_MODIFIER_SIDES_MERGED = True
DEFAULT_MODIFIER_KEY_DISPLAY = ModifierKeyDisplay.ORIGINAL


def _read_bool_setting(setting_key: str, default: bool) -> bool:
    raw = db_settings.get_setting(setting_key)
    if raw is None:
        return default
    return raw.strip().casefold() == "true"


def modifier_colouring_enabled() -> bool:
    """Master toggle "Colour by modifier key". Default off."""
    return _read_bool_setting(
        MODIFIER_COLOURING_SETTING_KEY, DEFAULT_MODIFIER_COLOURING
    )


def modifier_sides_merged() -> bool:
    """ "Treat left and right keys as the same" (L/R aliases active). Default on."""
    return _read_bool_setting(
        MODIFIER_SIDES_MERGED_SETTING_KEY, DEFAULT_MODIFIER_SIDES_MERGED
    )


def get_modifier_key_display() -> ModifierKeyDisplay:
    """How key names are displayed. Default ``ORIGINAL`` (as in the game)."""
    raw = db_settings.get_setting(MODIFIER_KEY_DISPLAY_SETTING_KEY)
    if raw is None:
        return DEFAULT_MODIFIER_KEY_DISPLAY
    try:
        return ModifierKeyDisplay(raw)
    except ValueError:
        _logger.warning(
            f"Invalid modifier key display in settings: {raw!r}, using default"
        )
        return DEFAULT_MODIFIER_KEY_DISPLAY


def set_modifier_colouring_enabled(enabled: bool) -> None:
    db_settings.add_update_setting_value(
        MODIFIER_COLOURING_SETTING_KEY, "true" if enabled else "false"
    )


def set_modifier_sides_merged(merged: bool) -> None:
    db_settings.add_update_setting_value(
        MODIFIER_SIDES_MERGED_SETTING_KEY, "true" if merged else "false"
    )


def set_modifier_key_display(display: ModifierKeyDisplay) -> None:
    db_settings.add_update_setting_value(
        MODIFIER_KEY_DISPLAY_SETTING_KEY, ModifierKeyDisplay(display).value
    )


# ── "Showing modifiers" (plan 2.2H) ───────────────────────────────────

MODIFIER_DISPLAY_SETTING_KEY = "modifier_display"
# The pre-existing Settings → General checkbox key. Still written on every
# change so a downgraded app keeps the user's choice.
LEGACY_MERGE_MODIFIERS_SETTING_KEY = "merge_modifiers_into_input"


class ModifierDisplay(str, Enum):
    """Where modifier bindings appear on a diagram."""

    TEMPLATE_BOXES = "TEMPLATE_BOXES"  # only where the template has modifier boxes
    UNDER_MAIN_TEXT = "UNDER_MAIN_TEXT"  # each on its own line under the main text
    MERGED_SAME_LINE = "MERGED_SAME_LINE"  # legacy " | " join on one line


DEFAULT_MODIFIER_DISPLAY = ModifierDisplay.TEMPLATE_BOXES


def get_modifier_display() -> ModifierDisplay:
    """The "Showing modifiers" choice, migrating from the legacy checkbox.

    A missing (or unreadable) new key falls back to the legacy key: ``"true"``
    maps to ``MERGED_SAME_LINE`` so migrated users keep today's output byte for
    byte; anything else is ``TEMPLATE_BOXES``.
    """
    raw = db_settings.get_setting(MODIFIER_DISPLAY_SETTING_KEY)
    if raw is not None:
        try:
            return ModifierDisplay(raw.strip())
        except ValueError:
            _logger.debug(f"Ignoring invalid modifier display setting {raw!r}")
    legacy = db_settings.get_setting(LEGACY_MERGE_MODIFIERS_SETTING_KEY)
    if legacy == "true":
        return ModifierDisplay.MERGED_SAME_LINE
    return DEFAULT_MODIFIER_DISPLAY


def modifiers_in_main_text(display: ModifierDisplay) -> bool:
    """Whether modifiers are folded into the main binding text (either merged mode)."""
    return ModifierDisplay(display) is not ModifierDisplay.TEMPLATE_BOXES


def set_modifier_display(display: ModifierDisplay) -> None:
    """Store the choice and mirror it into the legacy key for downgrade safety."""
    display = ModifierDisplay(display)
    db_settings.add_update_setting_value(MODIFIER_DISPLAY_SETTING_KEY, display.value)
    db_settings.add_update_setting_value(
        LEGACY_MERGE_MODIFIERS_SETTING_KEY,
        "true" if modifiers_in_main_text(display) else "false",
    )


# ── Display groups ─────────────────────────────────────────────────────


class ModifierKeyGroup(str, Enum):
    """Display-only grouping of a resolved modifier key."""

    KEYBOARD = "KEYBOARD"  # a keyboard key: Shift, Ctrl, "BMS DX Shift"...
    DEVICE_INPUT = "DEVICE_INPUT"  # a button/axis on a device: JOY_BTN3, BUTTON_5
    QUALIFIER = "QUALIFIER"  # a promoted label: profile/device name, "Long"


# Canonical name of the shared style all device-input keys take by default.
DEVICE_INPUT_CANONICAL = "Device buttons"

_DEVICE_INPUT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^joy_btn\d+$"),  # DCS: a button on another device
    re.compile(r"^joy_btn_pov\d+_[a-z]+$"),  # DCS: a hat direction on another device
    re.compile(r"^button_\d+$"),  # MSFS / Joystick Diagrams device-local id
    re.compile(r"^pov_\d+_[urdl]+$"),
    re.compile(r"^axis_(x|y|z|rx|ry|rz|slider|slider_\d+)$"),
)

UNKNOWN_KEY_PRIORITY = 100
QUALIFIER_PRIORITY = 1000


def is_device_input_key(raw: str) -> bool:
    """True for keys that name a button/axis/hat on a device rather than a keyboard key."""
    token = normalise_token(raw)
    return any(pattern.match(token) for pattern in _DEVICE_INPUT_PATTERNS)


def group_of(raw: str, kind: ModifierKind = ModifierKind.KEY) -> ModifierKeyGroup:
    """Classify a raw modifier key for display purposes."""
    if ModifierKind(kind) is ModifierKind.QUALIFIER:
        return ModifierKeyGroup.QUALIFIER
    if is_device_input_key(raw):
        return ModifierKeyGroup.DEVICE_INPUT
    return ModifierKeyGroup.KEYBOARD


# ── Colour helpers ─────────────────────────────────────────────────────

_HEX_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex_colour(value: str) -> bool:
    return bool(_HEX_COLOUR.match(value))


def _channels(hex_colour: str) -> tuple[int, int, int]:
    value = hex_colour.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _relative_luminance(hex_colour: str) -> float:
    def linear(channel: int) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _channels(hex_colour)
    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2.x contrast ratio between two ``#RRGGBB`` colours (1.0 to 21.0)."""
    fg, bg = _relative_luminance(foreground), _relative_luminance(background)
    lighter, darker = max(fg, bg), min(fg, bg)
    return (lighter + 0.05) / (darker + 0.05)


def text_safe_colour(
    hex_colour: str, background: str = "#FFFFFF", minimum_ratio: float = 4.5
) -> str:
    """Darken (or lighten, on dark backgrounds) a colour until it is legible as text.

    The hue is kept by scaling all channels together. Returns the input when it
    already meets ``minimum_ratio`` (WCAG AA for normal text is 4.5).
    """
    if contrast_ratio(hex_colour, background) >= minimum_ratio:
        return hex_colour.upper()

    darken = _relative_luminance(background) >= 0.5
    r, g, b = _channels(hex_colour)
    for step in range(1, 100):
        scale = 1 - step / 100
        if darken:
            candidate = (int(r * scale), int(g * scale), int(b * scale))
        else:
            candidate = tuple(int(c + (255 - c) * (1 - scale)) for c in (r, g, b))
        candidate_hex = "#{:02X}{:02X}{:02X}".format(*candidate)
        if contrast_ratio(candidate_hex, background) >= minimum_ratio:
            return candidate_hex
    return "#000000" if darken else "#FFFFFF"


# ── Registry rows ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class ModifierKeyStyle:
    """The style of one registry group. One JSON column in the database.

    ``colour`` is the group's colour for strokes and fills. ``text_colour`` is
    a darker variant that is legible as text on white; when ``None`` it is
    derived from ``colour`` with ``text_safe_colour``.
    """

    colour: str
    text_colour: str | None = None

    def __post_init__(self):
        if not is_hex_colour(self.colour):
            raise ValueError(f"colour must be #RRGGBB, got {self.colour!r}")
        if self.text_colour is not None and not is_hex_colour(self.text_colour):
            raise ValueError(f"text_colour must be #RRGGBB, got {self.text_colour!r}")

    @property
    def resolved_text_colour(self) -> str:
        return self.text_colour or text_safe_colour(self.colour)

    def to_json(self) -> str:
        return json.dumps({"colour": self.colour, "text_colour": self.text_colour})

    @classmethod
    def from_json(cls, raw: str | None) -> "ModifierKeyStyle | None":
        if not raw:
            return None
        try:
            data: dict[str, Any] = json.loads(raw)
            return cls(colour=data["colour"], text_colour=data.get("text_colour"))
        except (ValueError, KeyError, TypeError) as err:
            _logger.warning(f"Ignoring invalid modifier key style {raw!r}: {err}")
            return None


@dataclass(frozen=True)
class ModifierKeyInfo:
    """A registry group: the row keyed by ``(kind, canonical)``."""

    kind: ModifierKind
    canonical: str
    display_label: str | None = None
    priority: int = UNKNOWN_KEY_PRIORITY
    style: ModifierKeyStyle | None = None
    builtin: bool = False

    @property
    def key(self) -> tuple[ModifierKind, str]:
        return (self.kind, self.canonical)


@dataclass(frozen=True)
class ModifierKeyAlias:
    """A raw spelling that resolves to a group. ``alias`` is normalised."""

    alias: str
    canonical: str
    kind: ModifierKind = ModifierKind.KEY
    display_label: str | None = None
    side_alias: bool = False
    builtin: bool = False


# ── Seeds (pure data) ──────────────────────────────────────────────────

SEED_VERSION = 1

# Okabe-Ito colour-blind-safe palette with text-safe variants (>= 4.5:1 on white).
OKABE_ITO: Mapping[str, ModifierKeyStyle] = MappingProxyType(
    {
        "Shift": ModifierKeyStyle("#0072B2", "#005B8E"),
        "Ctrl": ModifierKeyStyle("#D55E00", "#A84300"),
        "Alt": ModifierKeyStyle("#009E73", "#00694D"),
        "Win": ModifierKeyStyle("#CC79A7", "#8C3D6B"),
        DEVICE_INPUT_CANONICAL: ModifierKeyStyle("#56B4E9", "#3C7DA3"),
    }
)


def _seed_group(
    canonical: str, priority: int, label: str | None = None
) -> ModifierKeyInfo:
    return ModifierKeyInfo(
        kind=ModifierKind.KEY,
        canonical=canonical,
        display_label=label or canonical,
        priority=priority,
        style=OKABE_ITO[canonical],
        builtin=True,
    )


# (since seed version, row). Priority drives combo order Ctrl+Alt+Shift+Win and
# equals the built-in rank in input/modifier.py so the order never changes twice.
SEED_MODIFIER_KEYS: tuple[tuple[int, ModifierKeyInfo], ...] = (
    (1, _seed_group("Ctrl", 10)),
    (1, _seed_group("Alt", 20)),
    (1, _seed_group("Shift", 30)),
    (1, _seed_group("Win", 40)),
    (1, _seed_group(DEVICE_INPUT_CANONICAL, 50)),
)


def _plain_aliases(
    canonical: str, *spellings: str
) -> list[tuple[int, ModifierKeyAlias]]:
    return [
        (1, ModifierKeyAlias(normalise_token(s), canonical, builtin=True))
        for s in spellings
    ]


def _side_aliases(canonical: str, *bases: str) -> list[tuple[int, ModifierKeyAlias]]:
    rows: list[tuple[int, ModifierKeyAlias]] = []
    for base in bases:
        for prefix, side in (
            ("l", "L"),
            ("r", "R"),
            ("left ", "L"),
            ("right ", "R"),
            ("l-", "L"),
            ("r-", "R"),
        ):
            rows.append(
                (
                    1,
                    ModifierKeyAlias(
                        alias=normalise_token(prefix + base),
                        canonical=canonical,
                        display_label=f"{side} {canonical}",
                        side_alias=True,
                        builtin=True,
                    ),
                )
            )
    return rows


# The canonical spelling itself ("shift", "ctrl"...) needs no alias row: group
# names match case-insensitively, and a self-alias would read as a chain.
SEED_ALIASES: tuple[tuple[int, ModifierKeyAlias], ...] = tuple(
    _plain_aliases("Ctrl", "control")
    + _side_aliases("Ctrl", "ctrl", "control")
    + _side_aliases("Alt", "alt")
    + _side_aliases("Shift", "shift")
    + _plain_aliases("Win", "meta", "super", "cmd")
    + _side_aliases("Win", "win")
)


# ── Snapshot ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ModifierRegistrySnapshot:
    """Frozen view of the registry plus the settings that affect resolution.

    Built by ``ModifierKeyService.snapshot()`` (which reads the settings at
    call time) or by ``ModifierRegistrySnapshot.default()`` from the seeds.
    """

    groups: Mapping[tuple[ModifierKind, str], ModifierKeyInfo]
    aliases: Mapping[str, ModifierKeyAlias]
    sides_merged: bool = DEFAULT_MODIFIER_SIDES_MERGED
    colouring_enabled: bool = DEFAULT_MODIFIER_COLOURING
    key_display: ModifierKeyDisplay = DEFAULT_MODIFIER_KEY_DISPLAY
    _canonical_index: Mapping[str, ModifierKeyInfo] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self):
        index = {
            normalise_token(info.canonical): info
            for info in self.groups.values()
            if info.kind is ModifierKind.KEY
        }
        object.__setattr__(self, "groups", MappingProxyType(dict(self.groups)))
        object.__setattr__(self, "aliases", MappingProxyType(dict(self.aliases)))
        object.__setattr__(self, "_canonical_index", MappingProxyType(index))

    @classmethod
    def build(
        cls,
        groups: Iterable[ModifierKeyInfo],
        aliases: Iterable[ModifierKeyAlias],
        *,
        sides_merged: bool | None = None,
        colouring_enabled: bool | None = None,
        key_display: ModifierKeyDisplay | None = None,
    ) -> "ModifierRegistrySnapshot":
        """Build a snapshot; any flag left ``None`` is read from settings now."""
        return cls(
            groups={info.key: info for info in groups},
            aliases={alias.alias: alias for alias in aliases},
            sides_merged=modifier_sides_merged()
            if sides_merged is None
            else sides_merged,
            colouring_enabled=(
                modifier_colouring_enabled()
                if colouring_enabled is None
                else colouring_enabled
            ),
            key_display=get_modifier_key_display()
            if key_display is None
            else key_display,
        )

    @classmethod
    def default(
        cls,
        *,
        sides_merged: bool = DEFAULT_MODIFIER_SIDES_MERGED,
        colouring_enabled: bool = DEFAULT_MODIFIER_COLOURING,
        key_display: ModifierKeyDisplay = DEFAULT_MODIFIER_KEY_DISPLAY,
    ) -> "ModifierRegistrySnapshot":
        """A snapshot of the seed data only; no database access."""
        return cls(
            groups={info.key: info for _, info in SEED_MODIFIER_KEYS},
            aliases={alias.alias: alias for _, alias in SEED_ALIASES},
            sides_merged=sides_merged,
            colouring_enabled=colouring_enabled,
            key_display=key_display,
        )

    def group(self, kind: ModifierKind, canonical: str) -> ModifierKeyInfo | None:
        return self.groups.get((ModifierKind(kind), canonical))

    def group_by_name(self, name: str) -> ModifierKeyInfo | None:
        """Case-insensitive lookup of a KEY-kind group by canonical name."""
        return self._canonical_index.get(normalise_token(name))

    def alias(self, raw: str) -> ModifierKeyAlias | None:
        """The alias row for ``raw``, honouring the L/R toggle (``None`` if skipped)."""
        row = self.aliases.get(normalise_token(raw))
        if row is None or (row.side_alias and not self.sides_merged):
            return None
        return row


# ── Resolution ─────────────────────────────────────────────────────────


def canonical_of(
    raw: str,
    snapshot: ModifierRegistrySnapshot,
    kind: ModifierKind = ModifierKind.KEY,
) -> tuple[ModifierKind, str]:
    """Resolve a raw key to its registry identity ``(kind, canonical)``."""
    kind = ModifierKind(kind)
    if kind is ModifierKind.QUALIFIER:
        return (ModifierKind.QUALIFIER, raw)

    alias = snapshot.alias(raw)
    if alias is not None:
        return (ModifierKind.KEY, alias.canonical)

    by_name = snapshot.group_by_name(raw)
    if by_name is not None:
        return by_name.key

    if is_device_input_key(raw) and snapshot.group(
        ModifierKind.KEY, DEVICE_INPUT_CANONICAL
    ):
        return (ModifierKind.KEY, DEVICE_INPUT_CANONICAL)

    return (ModifierKind.KEY, raw)


def canonical_keys(
    modifier: Modifier, snapshot: ModifierRegistrySnapshot
) -> tuple[tuple[ModifierKind, str], ...]:
    """Identities of every key in ``modifier``, in built-in rank order."""
    return tuple(
        canonical_of(raw, snapshot, modifier.kind) for raw in modifier.sorted_keys
    )


@dataclass(frozen=True)
class ResolvedModifierKey:
    """One raw key resolved against the registry. What a renderer needs per run."""

    raw: str
    kind: ModifierKind
    canonical: str
    group: ModifierKeyGroup
    display_label: str  # keeps the side: "L Ctrl"; raw under ORIGINAL display
    priority: int
    side: str | None  # "L", "R" or None
    style: ModifierKeyStyle | None  # the registry style, even when colouring is off
    colour: str | None  # effective colour: None when off, qualifier or unstyled
    text_colour: str | None  # effective text colour, same rules as colour

    @property
    def identity(self) -> tuple[ModifierKind, str]:
        return (self.kind, self.canonical)


def _simplified_label(
    raw: str,
    info: ModifierKeyInfo | None,
    alias: ModifierKeyAlias | None,
    group: ModifierKeyGroup,
) -> str:
    """Alias label, then side + group label, then group label, then raw."""
    if alias is not None and alias.display_label:
        return alias.display_label
    if group is ModifierKeyGroup.DEVICE_INPUT or info is None:
        return raw  # "Device buttons" must never replace "JOY_BTN3"
    base_label = info.display_label or info.canonical
    side, _ = split_side(raw)
    if alias is not None and alias.side_alias and side:
        return f"{side} {base_label}"
    return base_label


def resolve_key(
    raw: str,
    snapshot: ModifierRegistrySnapshot,
    kind: ModifierKind = ModifierKind.KEY,
) -> ResolvedModifierKey:
    """Resolve one raw key: identity, group, label, priority and effective colour."""
    kind = ModifierKind(kind)
    group = group_of(raw, kind)
    identity = canonical_of(raw, snapshot, kind)
    info = snapshot.group(*identity)
    alias = snapshot.alias(raw) if kind is ModifierKind.KEY else None
    side, _ = split_side(raw)

    if kind is ModifierKind.QUALIFIER:
        priority = info.priority if info else QUALIFIER_PRIORITY
    else:
        priority = info.priority if info else UNKNOWN_KEY_PRIORITY

    label = raw
    if (
        kind is ModifierKind.KEY
        and snapshot.key_display is ModifierKeyDisplay.SIMPLIFIED
    ):
        label = _simplified_label(raw, info, alias, group)

    style = info.style if info else None
    coloured = (
        snapshot.colouring_enabled and kind is ModifierKind.KEY and style is not None
    )

    return ResolvedModifierKey(
        raw=raw,
        kind=identity[0],
        canonical=identity[1],
        group=group,
        display_label=label,
        priority=priority,
        side=side,
        style=style,
        colour=style.colour if coloured and style else None,
        text_colour=style.resolved_text_colour if coloured and style else None,
    )


@dataclass(frozen=True)
class ResolvedModifier:
    """A key combination resolved for rendering.

    ``keys`` are ordered by registry priority, then the built-in rank. ``colour``
    is the colour of the highest-priority key (lowest priority number) that has
    one; ``primary`` is that key. ``text`` joins the display labels with ``+``.
    """

    keys: tuple[ResolvedModifierKey, ...]
    primary: ResolvedModifierKey | None
    colour: str | None
    text_colour: str | None
    text: str

    @property
    def groups(self) -> tuple[ModifierKeyGroup, ...]:
        return tuple(dict.fromkeys(key.group for key in self.keys))

    @property
    def identities(self) -> tuple[tuple[ModifierKind, str], ...]:
        return tuple(key.identity for key in self.keys)


def _ordering(resolved: ResolvedModifierKey) -> tuple:
    return (resolved.priority, modifier_sort_key(resolved.raw))


def resolve_keys(
    raw_keys: Iterable[str],
    snapshot: ModifierRegistrySnapshot,
    kind: ModifierKind = ModifierKind.KEY,
) -> ResolvedModifier:
    """Resolve a raw key set (all of one ``kind``) for rendering."""
    keys = tuple(
        sorted((resolve_key(raw, snapshot, kind) for raw in raw_keys), key=_ordering)
    )
    primary = next((key for key in keys if key.colour is not None), None)
    return ResolvedModifier(
        keys=keys,
        primary=primary,
        colour=primary.colour if primary else None,
        text_colour=primary.text_colour if primary else None,
        text="+".join(key.display_label for key in keys),
    )


def resolve_modifier(
    modifier: Modifier, snapshot: ModifierRegistrySnapshot
) -> ResolvedModifier:
    """Resolve a ``Modifier`` for rendering. Qualifier modifiers are never coloured."""
    return resolve_keys(modifier.modifiers, snapshot, modifier.kind)


def combo_style(
    canonicals: Iterable[tuple[ModifierKind, str]],
    snapshot: ModifierRegistrySnapshot,
) -> ModifierKeyStyle | None:
    """Style of the highest-priority (lowest number) KEY identity that has one.

    Ignores the colouring master toggle: this is the registry answer, used by
    the UI as well as the renderer. Qualifier identities never contribute.
    """
    best: ModifierKeyInfo | None = None
    for kind, canonical in canonicals:
        info = snapshot.group(kind, canonical)
        if info is None or info.kind is not ModifierKind.KEY or info.style is None:
            continue
        if best is None or info.priority < best.priority:
            best = info
    return best.style if best else None


# ── Discovery ──────────────────────────────────────────────────────────


@dataclass
class DiscoveredModifierKey:
    """A raw modifier key seen in the loaded profiles, with where it came from."""

    raw: str
    kind: ModifierKind
    count: int = 0
    plugins: dict[str, int] = field(default_factory=dict)  # plugin name -> binds
    sources: set[str] = field(default_factory=set)  # Modifier.source values seen

    @property
    def identity(self) -> tuple[ModifierKind, str]:
        return (self.kind, self.raw)

    @property
    def group(self) -> ModifierKeyGroup:
        return group_of(self.raw, self.kind)


def _wrapper_plugin_name(wrapper: Any) -> str:
    origin = getattr(wrapper, "profile_origin", None)
    name = getattr(origin, "name", None)
    return str(name) if name else "an unknown game"


def _iter_modifiers(profile: Any) -> Iterable[Modifier]:
    for device in getattr(profile, "devices", {}).values():
        for input_ in device.get_combined_inputs().values():
            yield from input_.modifiers


def discover_modifier_keys(
    profile_wrappers: Iterable[Any],
) -> list[DiscoveredModifierKey]:
    """Scan profile wrappers for every raw modifier key with per-plugin counts.

    Feeds a future "Keys found in your profiles" UI. Sorted by count (desc),
    then kind, then raw spelling, so the result is deterministic.
    """
    found: dict[tuple[ModifierKind, str], DiscoveredModifierKey] = {}
    for wrapper in profile_wrappers:
        profile = getattr(wrapper, "profile", None)
        if profile is None:
            continue
        plugin = _wrapper_plugin_name(wrapper)
        for modifier in _iter_modifiers(profile):
            for raw in modifier.modifiers:
                entry = found.setdefault(
                    (modifier.kind, raw), DiscoveredModifierKey(raw, modifier.kind)
                )
                entry.count += 1
                entry.plugins[plugin] = entry.plugins.get(plugin, 0) + 1
                if modifier.source:
                    entry.sources.add(modifier.source)
    return sorted(found.values(), key=lambda d: (-d.count, d.kind.value, d.raw))
