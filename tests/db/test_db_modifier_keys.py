"""Tests for the modifier key registry DB layer and ModifierKeyService.

Follows tests/db/test_device_alias_service.py: the db module's `connection`
is patched with an in-memory sqlite. Settings are backed by a dict so seed
gating (`modifier_keys_seed_version`) can be exercised across "restarts".
"""

import sqlite3
from unittest.mock import patch

import pytest

from joystick_diagrams.db import db_modifier_keys
from joystick_diagrams.db.modifier_key_service import ModifierKeyService
from joystick_diagrams.input.modifier import Modifier, ModifierKind
from joystick_diagrams.modifier_identity import (
    DEVICE_INPUT_CANONICAL,
    MODIFIER_KEYS_SEED_VERSION_SETTING_KEY,
    SEED_ALIASES,
    SEED_MODIFIER_KEYS,
    SEED_VERSION,
    ModifierKeyInfo,
    ModifierKeyStyle,
)

# ── DB layer fixtures & tests ──────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_connection():
    conn = sqlite3.connect(":memory:")
    with patch("joystick_diagrams.db.db_modifier_keys.connection", return_value=conn):
        db_modifier_keys.create_new_db_if_not_exist()
        yield conn
    conn.close()


_GROUP_DEFAULTS = {
    "kind": "KEY",
    "canonical": "Shift",
    "label": "Shift",
    "priority": 30,
    "style": None,
    "builtin": 0,
}
_ALIAS_DEFAULTS = {
    "alias": "lshift",
    "canonical": "Shift",
    "kind": "KEY",
    "label": "L Shift",
    "side": 1,
    "builtin": 0,
}


def _group_row(kind=None, canonical=None, **overrides):
    """(kind, canonical, display_label, priority, style_json, builtin) with defaults."""
    values = {**_GROUP_DEFAULTS, **overrides}
    values["kind"] = kind or values["kind"]
    values["canonical"] = canonical or values["canonical"]
    return tuple(values[k] for k in _GROUP_DEFAULTS)


def _alias_row(alias=None, **overrides):
    """(alias, canonical, kind, display_label, side_alias, builtin) with defaults."""
    values = {**_ALIAS_DEFAULTS, **overrides}
    values["alias"] = alias or values["alias"]
    return tuple(values[k] for k in _ALIAS_DEFAULTS)


class TestDBModifierKeys:
    def test_tables_exist(self, mock_connection):
        cur = mock_connection.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {row[0] for row in cur.fetchall()}
        assert {"modifier_keys", "modifier_key_aliases"} <= names

    def test_group_pk_is_kind_plus_canonical(self):
        db_modifier_keys.upsert_modifier_key(_group_row("KEY", "Shift"))
        db_modifier_keys.upsert_modifier_key(
            _group_row("QUALIFIER", "Shift", label="Profile Shift", priority=1000)
        )
        rows = db_modifier_keys.get_all_modifier_keys()
        assert [(r[0], r[1]) for r in rows] == [
            ("KEY", "Shift"),
            ("QUALIFIER", "Shift"),
        ]

    def test_upsert_replace_and_ignore(self):
        db_modifier_keys.upsert_modifier_key(_group_row(label="Shift", priority=30))
        db_modifier_keys.upsert_modifier_key(
            _group_row(label="Changed", priority=5), replace=False
        )
        assert db_modifier_keys.get_all_modifier_keys()[0][2] == "Shift"
        db_modifier_keys.upsert_modifier_key(_group_row(label="Changed", priority=5))
        assert db_modifier_keys.get_all_modifier_keys()[0][2] == "Changed"

    def test_delete_group(self):
        db_modifier_keys.upsert_modifier_key(_group_row())
        db_modifier_keys.delete_modifier_key("KEY", "Shift")
        assert db_modifier_keys.get_all_modifier_keys() == []

    def test_alias_crud_and_delete_for_canonical(self):
        db_modifier_keys.upsert_alias(_alias_row("lshift"))
        db_modifier_keys.upsert_alias(_alias_row("rshift", label="R Shift"))
        db_modifier_keys.upsert_alias(
            _alias_row("lctrl", canonical="Ctrl", label="L Ctrl")
        )
        assert [r[0] for r in db_modifier_keys.get_all_aliases()] == [
            "lctrl",
            "lshift",
            "rshift",
        ]
        db_modifier_keys.delete_alias("lshift")
        assert [r[0] for r in db_modifier_keys.get_all_aliases()] == ["lctrl", "rshift"]
        db_modifier_keys.delete_aliases_for_canonical("KEY", "Shift")
        assert [r[0] for r in db_modifier_keys.get_all_aliases()] == ["lctrl"]


# ── Service layer fixtures & tests ─────────────────────────────────────


@pytest.fixture()
def settings_store():
    """Dict-backed stand-in for the settings table (the conftest autouse patch
    makes get_setting return None, which would re-seed on every start)."""
    store: dict[str, str] = {}
    with (
        patch(
            "joystick_diagrams.db.db_settings.get_setting",
            side_effect=store.get,
        ),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value",
            side_effect=store.__setitem__,
        ),
    ):
        yield store


@pytest.fixture()
def service(mock_connection, settings_store) -> ModifierKeyService:
    return ModifierKeyService()


class TestSeeding:
    def test_first_start_seeds_and_stores_version(self, service, settings_store):
        assert settings_store[MODIFIER_KEYS_SEED_VERSION_SETTING_KEY] == str(
            SEED_VERSION
        )
        assert len(service.get_groups()) == len(SEED_MODIFIER_KEYS)
        assert len(service.get_aliases()) == len(SEED_ALIASES)
        assert service.get_group(ModifierKind.KEY, "Shift").style.colour == "#0072B2"
        assert all(g.builtin for g in service.get_groups())

    def test_deleted_alias_stays_deleted_after_restart(self, service, settings_store):
        service.remove_alias("LShift")
        assert "lshift" not in {a.alias for a in service.get_aliases()}

        restarted = ModifierKeyService()  # same db, same settings store
        assert "lshift" not in {a.alias for a in restarted.get_aliases()}
        assert len(restarted.get_aliases()) == len(SEED_ALIASES) - 1

    def test_edited_builtin_not_overwritten_on_restart(self, service):
        service.set_style(ModifierKind.KEY, "Shift", ModifierKeyStyle("#123456"))
        restarted = ModifierKeyService()
        assert restarted.get_group(ModifierKind.KEY, "Shift").style.colour == "#123456"

    def test_restore_defaults_reinserts_everything(self, service):
        service.remove_alias("lshift")
        service.set_style(ModifierKind.KEY, "Shift", ModifierKeyStyle("#123456"))
        service.delete_group(ModifierKind.KEY, "Alt")

        service.restore_defaults()

        assert "lshift" in {a.alias for a in service.get_aliases()}
        assert service.get_group(ModifierKind.KEY, "Shift").style.colour == "#0072B2"
        assert service.get_group(ModifierKind.KEY, "Alt") is not None
        assert len(service.get_aliases()) == len(SEED_ALIASES)

    def test_newer_stored_version_skips_seeding(self, mock_connection, settings_store):
        settings_store[MODIFIER_KEYS_SEED_VERSION_SETTING_KEY] = str(SEED_VERSION)
        fresh = ModifierKeyService()
        assert fresh.get_groups() == []


class TestServiceGroups:
    def test_set_group_writes_through_and_caches(self, service):
        info = ModifierKeyInfo(
            ModifierKind.KEY, "AltGr", "AltGr", 25, ModifierKeyStyle("#AA0000")
        )
        stored = service.set_group(info)
        assert stored.builtin is False
        assert service.get_group(ModifierKind.KEY, "AltGr") == stored
        rows = {(r[0], r[1]) for r in db_modifier_keys.get_all_modifier_keys()}
        assert ("KEY", "AltGr") in rows

    def test_qualifier_group_can_share_a_name_with_a_key_group(self, service):
        service.set_group(
            ModifierKeyInfo(ModifierKind.QUALIFIER, "Shift", "Shift (profile)", 1000)
        )
        assert service.get_group(ModifierKind.QUALIFIER, "Shift") is not None
        assert service.get_group(ModifierKind.KEY, "Shift").style.colour == "#0072B2"

    def test_group_name_cannot_equal_an_alias(self, service):
        with pytest.raises(ValueError, match="already an alias"):
            service.set_group(ModifierKeyInfo(ModifierKind.KEY, "LShift"))

    def test_group_name_cannot_differ_only_by_case(self, service):
        with pytest.raises(ValueError, match="already exists"):
            service.set_group(ModifierKeyInfo(ModifierKind.KEY, "SHIFT"))

    def test_empty_group_name_rejected(self, service):
        with pytest.raises(ValueError, match="needs a name"):
            service.set_group(ModifierKeyInfo(ModifierKind.KEY, "   "))

    def test_set_priority_and_style_on_existing(self, service):
        service.set_priority(ModifierKind.KEY, "Shift", 5)
        service.set_style(ModifierKind.KEY, "Shift", None)
        shift = service.get_group(ModifierKind.KEY, "Shift")
        assert shift.priority == 5
        assert shift.style is None
        assert service.get_groups()[0].canonical == "Shift"
        with pytest.raises(ValueError, match="no modifier key group"):
            service.set_priority(ModifierKind.KEY, "Nope", 1)

    def test_delete_group_removes_its_aliases(self, service):
        assert service.aliases_for(ModifierKind.KEY, "Shift")
        service.delete_group(ModifierKind.KEY, "Shift")
        assert service.get_group(ModifierKind.KEY, "Shift") is None
        assert service.aliases_for(ModifierKind.KEY, "Shift") == []
        assert "lshift" not in {r[0] for r in db_modifier_keys.get_all_aliases()}


class TestServiceAliases:
    def test_set_alias_normalises_and_writes_through(self, service):
        row = service.set_alias("  BMS DX  Shift ", "shift")
        assert row.alias == "bms dx shift"
        assert row.canonical == "Shift"
        assert row.side_alias is False
        assert "bms dx shift" in {r[0] for r in db_modifier_keys.get_all_aliases()}
        assert service.snapshot().alias("BMS DX Shift").canonical == "Shift"

    def test_self_alias_rejected(self, service):
        with pytest.raises(ValueError, match="itself"):
            service.set_alias("shift", "Shift")
        with pytest.raises(ValueError, match="itself"):
            service.set_alias("SHIFT", "Shift")

    def test_unknown_target_rejected(self, service):
        with pytest.raises(ValueError, match="no modifier key group"):
            service.set_alias("foo", "Hyper")

    def test_chained_alias_rejected(self, service):
        with pytest.raises(ValueError, match="chained"):
            service.set_alias("foo", "lshift")

    def test_alias_shadowing_another_group_rejected(self, service):
        with pytest.raises(ValueError, match="cannot be an alias"):
            service.set_alias("Ctrl", "Shift")

    def test_overwrite_existing_alias_keeps_builtin_flag(self, service):
        row = service.set_alias(
            "lshift", "Ctrl", display_label="Weird", side_alias=True
        )
        assert row.builtin is True
        assert row.canonical == "Ctrl"
        assert service.snapshot().alias("LShift").display_label == "Weird"

    def test_remove_alias_is_write_through(self, service):
        service.remove_alias("LShift")
        assert "lshift" not in {r[0] for r in db_modifier_keys.get_all_aliases()}
        assert service.snapshot().alias("LShift") is None


class TestServiceResolution:
    def test_snapshot_reads_flags_at_call_time(self, service, settings_store):
        assert service.snapshot().colouring_enabled is False
        settings_store["modifier_colouring_enabled"] = "true"
        settings_store["modifier_lr_same"] = "false"
        snapshot = service.snapshot()
        assert snapshot.colouring_enabled is True
        assert snapshot.sides_merged is False

    def test_resolve_modifier_end_to_end(self, service, settings_store):
        settings_store["modifier_colouring_enabled"] = "true"
        resolved = service.resolve(Modifier({"LShift", "JOY_BTN3"}, "Fire"))
        assert [k.canonical for k in resolved.keys] == ["Shift", DEVICE_INPUT_CANONICAL]
        assert resolved.colour == "#0072B2"
        qualifier = service.resolve(
            Modifier({"Shift"}, "x", kind=ModifierKind.QUALIFIER, source="profile")
        )
        assert qualifier.colour is None

    def test_discover_delegates(self, service):
        assert service.discover([]) == []
