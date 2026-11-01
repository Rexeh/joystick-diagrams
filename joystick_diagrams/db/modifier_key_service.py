"""Cached, write-through access to the modifier key registry.

Mirrors ``DeviceAliasService``: a dict cache loaded once, every write goes to
the database and the cache together, and ``ValueError`` is raised for invalid
aliases (self-alias, chains, unknown targets, shadowing a group name).

Seeds from ``modifier_identity`` are inserted **once per seed version**, gated
by the ``modifier_keys_seed_version`` setting, so an alias the user deleted
stays deleted across restarts. ``restore_defaults()`` re-inserts them all.
"""

import logging
from collections.abc import Iterable
from typing import Any

from joystick_diagrams.db import db_modifier_keys, db_settings
from joystick_diagrams.input.modifier import Modifier, ModifierKind, normalise_token
from joystick_diagrams.modifier_identity import (
    MODIFIER_KEYS_SEED_VERSION_SETTING_KEY,
    SEED_ALIASES,
    SEED_MODIFIER_KEYS,
    SEED_VERSION,
    DiscoveredModifierKey,
    ModifierKeyAlias,
    ModifierKeyInfo,
    ModifierKeyStyle,
    ModifierRegistrySnapshot,
    ResolvedModifier,
    discover_modifier_keys,
    resolve_modifier,
)

_logger = logging.getLogger(__name__)


class ModifierKeyService:
    def __init__(self):
        self._groups: dict[tuple[ModifierKind, str], ModifierKeyInfo] = {}
        self._aliases: dict[str, ModifierKeyAlias] = {}  # normalised alias -> row
        self._seed_if_needed()
        self._load_cache()

    # ── Loading and seeding ────────────────────────────────────────────

    def _load_cache(self) -> None:
        self._groups = {
            info.key: info
            for info in (
                _row_to_info(row) for row in db_modifier_keys.get_all_modifier_keys()
            )
        }
        self._aliases = {
            alias.alias: alias
            for alias in (
                _row_to_alias(row) for row in db_modifier_keys.get_all_aliases()
            )
        }
        _logger.info(
            f"Loaded {len(self._groups)} modifier key groups and {len(self._aliases)} aliases from database"
        )

    def _seed_if_needed(self) -> None:
        """Insert seeds added after the stored seed version, then store the version."""
        stored = db_settings.get_setting(MODIFIER_KEYS_SEED_VERSION_SETTING_KEY)
        stored_version = int(stored) if stored and stored.strip().isdigit() else 0
        if stored_version >= SEED_VERSION:
            return

        self._insert_seeds(after_version=stored_version, replace=False)
        db_settings.add_update_setting_value(
            MODIFIER_KEYS_SEED_VERSION_SETTING_KEY, str(SEED_VERSION)
        )
        _logger.info(
            f"Seeded modifier keys from version {stored_version} to {SEED_VERSION}"
        )

    def _insert_seeds(self, *, after_version: int, replace: bool) -> None:
        for since, info in SEED_MODIFIER_KEYS:
            if since > after_version:
                _write_group(info, replace=replace)
        for since, alias in SEED_ALIASES:
            if since > after_version:
                _write_alias(alias, replace=replace)

    def restore_defaults(self) -> None:
        """Re-insert every seed row explicitly, overwriting edits to built-in rows."""
        self._insert_seeds(after_version=0, replace=True)
        db_settings.add_update_setting_value(
            MODIFIER_KEYS_SEED_VERSION_SETTING_KEY, str(SEED_VERSION)
        )
        self._load_cache()

    # ── Read API ───────────────────────────────────────────────────────

    def snapshot(self) -> ModifierRegistrySnapshot:
        """Frozen registry view. The L/R, colouring and display flags are read now."""
        return ModifierRegistrySnapshot.build(
            self._groups.values(), self._aliases.values()
        )

    def resolve(self, modifier: Modifier) -> ResolvedModifier:
        """Resolve a modifier for rendering against a fresh snapshot."""
        return resolve_modifier(modifier, self.snapshot())

    def get_groups(self) -> list[ModifierKeyInfo]:
        return sorted(self._groups.values(), key=lambda g: (g.priority, g.canonical))

    def get_group(self, kind: ModifierKind, canonical: str) -> ModifierKeyInfo | None:
        return self._groups.get((ModifierKind(kind), canonical))

    def get_aliases(self) -> list[ModifierKeyAlias]:
        return sorted(self._aliases.values(), key=lambda a: a.alias)

    def aliases_for(self, kind: ModifierKind, canonical: str) -> list[ModifierKeyAlias]:
        kind = ModifierKind(kind)
        return [
            a for a in self.get_aliases() if a.kind is kind and a.canonical == canonical
        ]

    def discover(self, profile_wrappers: Iterable[Any]) -> list[DiscoveredModifierKey]:
        """Raw modifier keys found in the given profile wrappers, with counts per plugin."""
        return discover_modifier_keys(profile_wrappers)

    # ── Write API: groups ──────────────────────────────────────────────

    def set_group(self, info: ModifierKeyInfo) -> ModifierKeyInfo:
        """Create or update a group. Raises ``ValueError`` if the name is taken by an alias."""
        canonical = " ".join(info.canonical.split())
        if not canonical:
            raise ValueError("a modifier key group needs a name")

        if info.kind is ModifierKind.KEY:
            same_name = self._group_by_name(canonical)
            if same_name is not None and same_name.canonical != canonical:
                raise ValueError(
                    f"a group named {same_name.canonical!r} already exists"
                )
            clash = self._aliases.get(normalise_token(canonical))
            if clash is not None and normalise_token(
                clash.canonical
            ) != normalise_token(canonical):
                raise ValueError(
                    f"{canonical!r} is already an alias of {clash.canonical!r}"
                )

        stored = ModifierKeyInfo(
            kind=ModifierKind(info.kind),
            canonical=canonical,
            display_label=info.display_label,
            priority=int(info.priority),
            style=info.style,
            builtin=info.builtin,
        )
        _write_group(stored, replace=True)
        self._groups[stored.key] = stored
        return stored

    def set_style(
        self, kind: ModifierKind, canonical: str, style: ModifierKeyStyle | None
    ) -> ModifierKeyInfo:
        info = self._require_group(kind, canonical)
        return self.set_group(
            ModifierKeyInfo(
                info.kind,
                info.canonical,
                info.display_label,
                info.priority,
                style,
                info.builtin,
            )
        )

    def set_priority(
        self, kind: ModifierKind, canonical: str, priority: int
    ) -> ModifierKeyInfo:
        info = self._require_group(kind, canonical)
        return self.set_group(
            ModifierKeyInfo(
                info.kind,
                info.canonical,
                info.display_label,
                int(priority),
                info.style,
                info.builtin,
            )
        )

    def delete_group(self, kind: ModifierKind, canonical: str) -> None:
        """Delete a group and every alias pointing at it."""
        kind = ModifierKind(kind)
        db_modifier_keys.delete_aliases_for_canonical(kind.value, canonical)
        db_modifier_keys.delete_modifier_key(kind.value, canonical)
        self._groups.pop((kind, canonical), None)
        for alias_key, alias in list(self._aliases.items()):
            if alias.kind is kind and alias.canonical == canonical:
                del self._aliases[alias_key]

    # ── Write API: aliases ─────────────────────────────────────────────

    def set_alias(
        self,
        raw: str,
        canonical: str,
        *,
        display_label: str | None = None,
        side_alias: bool = False,
    ) -> ModifierKeyAlias:
        """Make ``raw`` resolve to the KEY group ``canonical``.

        Raises ``ValueError`` when the alias would equal its own target, the
        target group does not exist, the target is itself an alias (no chains),
        or the alias would shadow another group's name.
        """
        alias_key = normalise_token(raw)
        if not alias_key:
            raise ValueError("an alias needs a key name")

        chained = self._aliases.get(normalise_token(canonical))
        if chained is not None and normalise_token(
            chained.canonical
        ) != normalise_token(canonical):
            raise ValueError(
                f"{canonical!r} is already an alias of {chained.canonical!r} — chained aliases are not supported"
            )

        target = self._group_by_name(canonical)
        if target is None:
            raise ValueError(f"no modifier key group named {canonical!r}")

        if alias_key == normalise_token(target.canonical):
            raise ValueError("cannot alias a key to itself")

        shadowed = self._group_by_name(alias_key)
        if shadowed is not None:
            raise ValueError(
                f"{raw!r} is the name of the {shadowed.canonical!r} group and cannot be an alias"
            )

        existing = self._aliases.get(alias_key)
        row = ModifierKeyAlias(
            alias=alias_key,
            canonical=target.canonical,
            kind=ModifierKind.KEY,
            display_label=display_label,
            side_alias=side_alias,
            builtin=existing.builtin if existing else False,
        )
        _write_alias(row, replace=True)
        self._aliases[alias_key] = row
        return row

    def remove_alias(self, raw: str) -> None:
        alias_key = normalise_token(raw)
        db_modifier_keys.delete_alias(alias_key)
        self._aliases.pop(alias_key, None)

    # ── Helpers ────────────────────────────────────────────────────────

    def _group_by_name(self, name: str) -> ModifierKeyInfo | None:
        wanted = normalise_token(name)
        for info in self._groups.values():
            if (
                info.kind is ModifierKind.KEY
                and normalise_token(info.canonical) == wanted
            ):
                return info
        return None

    def _require_group(self, kind: ModifierKind, canonical: str) -> ModifierKeyInfo:
        info = self.get_group(kind, canonical)
        if info is None:
            raise ValueError(
                f"no modifier key group ({ModifierKind(kind).value}, {canonical!r})"
            )
        return info


# ── Row mapping ────────────────────────────────────────────────────────


def _row_to_info(row: db_modifier_keys.ModifierKeyRow) -> ModifierKeyInfo:
    kind, canonical, display_label, priority, style_json, builtin = row
    return ModifierKeyInfo(
        kind=ModifierKind(kind),
        canonical=canonical,
        display_label=display_label,
        priority=int(priority),
        style=ModifierKeyStyle.from_json(style_json),
        builtin=bool(builtin),
    )


def _row_to_alias(row: db_modifier_keys.ModifierKeyAliasRow) -> ModifierKeyAlias:
    alias, canonical, kind, display_label, side_alias, builtin = row
    return ModifierKeyAlias(
        alias=alias,
        canonical=canonical,
        kind=ModifierKind(kind),
        display_label=display_label,
        side_alias=bool(side_alias),
        builtin=bool(builtin),
    )


def _write_group(info: ModifierKeyInfo, *, replace: bool) -> None:
    db_modifier_keys.upsert_modifier_key(
        (
            info.kind.value,
            info.canonical,
            info.display_label,
            info.priority,
            info.style.to_json() if info.style else None,
            int(info.builtin),
        ),
        replace=replace,
    )


def _write_alias(alias: ModifierKeyAlias, *, replace: bool) -> None:
    db_modifier_keys.upsert_alias(
        (
            alias.alias,
            alias.canonical,
            alias.kind.value,
            alias.display_label,
            int(alias.side_alias),
            int(alias.builtin),
        ),
        replace=replace,
    )
