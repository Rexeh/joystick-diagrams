"""Tests for device alias DB CRUD and DeviceAliasService."""

import sqlite3
from unittest.mock import patch

import pytest

from joystick_diagrams.db import db_device_aliases
from joystick_diagrams.db.device_alias_service import DeviceAliasService

# ── DB layer fixtures & tests ──────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_connection():
    conn = sqlite3.connect(":memory:")
    with patch("joystick_diagrams.db.db_device_aliases.connection", return_value=conn):
        db_device_aliases.create_new_db_if_not_exist()
        yield conn
    conn.close()


class TestDBDeviceAliases:
    """Tests for the db_device_aliases CRUD layer."""

    def test_table_creation(self, mock_connection):
        """Table should exist after create_new_db_if_not_exist."""
        cur = mock_connection.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='device_aliases'"
        )
        assert cur.fetchone() is not None

    def test_add_alias_and_get_all(self, mock_connection):
        db_device_aliases.add_update_alias("guid-a", "guid-b")
        result = db_device_aliases.get_all_aliases()
        assert result == [("guid-a", "guid-b")]

    def test_update_existing_alias(self, mock_connection):
        db_device_aliases.add_update_alias("guid-a", "guid-b")
        db_device_aliases.add_update_alias("guid-a", "guid-c")
        result = db_device_aliases.get_all_aliases()
        assert result == [("guid-a", "guid-c")]

    def test_delete_alias(self, mock_connection):
        db_device_aliases.add_update_alias("guid-a", "guid-b")
        db_device_aliases.delete_alias("guid-a")
        result = db_device_aliases.get_all_aliases()
        assert result == []

    def test_empty_state(self, mock_connection):
        result = db_device_aliases.get_all_aliases()
        assert result == []

    def test_fan_in_multiple_sources_same_target(self, mock_connection):
        db_device_aliases.add_update_alias("guid-a", "guid-z")
        db_device_aliases.add_update_alias("guid-b", "guid-z")
        result = db_device_aliases.get_all_aliases()
        assert len(result) == 2
        assert ("guid-a", "guid-z") in result
        assert ("guid-b", "guid-z") in result


# ── Service layer fixtures & tests ─────────────────────────────────────


@pytest.fixture()
def alias_service(mock_connection):
    with patch(
        "joystick_diagrams.db.device_alias_service.db_device_aliases"
    ) as mock_db:
        mock_db.get_all_aliases = db_device_aliases.get_all_aliases
        mock_db.add_update_alias = db_device_aliases.add_update_alias
        mock_db.delete_alias = db_device_aliases.delete_alias
        yield DeviceAliasService()


class TestDeviceAliasService:
    """Tests for the DeviceAliasService."""

    def test_resolve_no_alias_returns_original(self, alias_service):
        assert alias_service.resolve("guid-x") == "guid-x"

    def test_resolve_with_alias_returns_target(self, alias_service):
        alias_service.set_alias("guid-a", "guid-b")
        assert alias_service.resolve("guid-a") == "guid-b"

    def test_set_alias_self_alias_rejected(self, alias_service):
        with pytest.raises(ValueError, match="cannot alias a device to itself"):
            alias_service.set_alias("guid-a", "guid-a")

    def test_set_alias_target_is_source_rejected(self, alias_service):
        """If A->B exists, set_alias(C, A) should be rejected because A is a source."""
        alias_service.set_alias("guid-a", "guid-b")
        with pytest.raises(ValueError, match="target is already aliased to"):
            alias_service.set_alias("guid-c", "guid-a")

    def test_set_alias_source_is_target_rejected(self, alias_service):
        """If A->B exists, set_alias(B, C) should be rejected because B is a target."""
        alias_service.set_alias("guid-a", "guid-b")
        with pytest.raises(
            ValueError, match="source is already a target of another alias"
        ):
            alias_service.set_alias("guid-b", "guid-c")

    def test_fan_in_allowed(self, alias_service):
        """If A->B exists, set_alias(C, B) should succeed (fan-in)."""
        alias_service.set_alias("guid-a", "guid-b")
        alias_service.set_alias("guid-c", "guid-b")
        assert alias_service.resolve("guid-a") == "guid-b"
        assert alias_service.resolve("guid-c") == "guid-b"

    def test_remove_alias(self, alias_service):
        alias_service.set_alias("guid-a", "guid-b")
        alias_service.remove_alias("guid-a")
        assert alias_service.resolve("guid-a") == "guid-a"

    def test_get_all_aliases_returns_cache_copy(self, alias_service):
        alias_service.set_alias("guid-a", "guid-b")
        aliases = alias_service.get_all_aliases()
        assert aliases == {"guid-a": "guid-b"}
        # Mutating returned dict should not affect internal cache
        aliases["guid-x"] = "guid-y"
        assert "guid-x" not in alias_service.get_all_aliases()

    def test_overwrite_existing_alias(self, alias_service):
        alias_service.set_alias("guid-a", "guid-b")
        alias_service.set_alias("guid-a", "guid-c")
        assert alias_service.resolve("guid-a") == "guid-c"
