"""``devices`` table columns, migrations and ``DeviceService`` (in-memory sqlite)."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from joystick_diagrams.db import db_device_management
from joystick_diagrams.db.db_device_management import (
    KIND_OTHER,
    KIND_REASON_LEGACY_HIDDEN,
    KIND_SOURCE_AUTO,
    KIND_SOURCE_USER,
)
from joystick_diagrams.db.device_service import KIND_JOYSTICK, DeviceService

GUID = "666ec0a0-556b-11ee-8002-444553540000"
GUID_2 = "777ec0a0-556b-11ee-8002-444553540000"
STARTER = Path("templates/Starter Template.svg")


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    with patch(
        "joystick_diagrams.db.db_device_management.connection",
        return_value=connection,
    ):
        yield connection
    connection.close()


@pytest.fixture
def fresh(conn):
    db_device_management.create_new_db_if_not_exist()
    return conn


def columns(conn) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(devices)")}


class TestMigrations:
    def test_fresh_table_has_every_column(self, fresh):
        assert {
            "kind",
            "kind_source",
            "kind_reason",
            "last_seen",
            "games_json",
            "template_key",
            "template_hash",
            "hidden",
            "custom_name",
        } <= columns(fresh)

    def test_legacy_table_is_upgraded_in_place(self, conn):
        conn.execute(
            "CREATE TABLE devices(guid TEXT PRIMARY KEY, template_path TEXT, name TEXT, hidden BOOLEAN DEFAULT 0)"
        )
        conn.execute(
            "INSERT INTO devices VALUES (?, ?, ?, 1)", (GUID, str(STARTER), "Keyboard")
        )
        conn.execute("INSERT INTO devices VALUES (?, NULL, 'Stick', 0)", (GUID_2,))
        conn.commit()
        db_device_management.create_new_db_if_not_exist()
        row = db_device_management.get_device_row(GUID)
        # hidden=1 became a user "No diagram" with the legacy reason
        assert (row.kind, row.kind_source, row.kind_reason) == (
            KIND_OTHER,
            KIND_SOURCE_USER,
            KIND_REASON_LEGACY_HIDDEN,
        )
        assert row.hidden is True
        # template_key / template_hash were derived from the stored path
        assert row.template_key == "bundled:Starter Template.svg"
        assert row.template_hash and len(row.template_hash) == 64
        other = db_device_management.get_device_row(GUID_2)
        assert other.kind is None and other.hidden is False
        assert other.template_key is None
        # Running the migration again changes nothing
        db_device_management.create_new_db_if_not_exist()
        assert db_device_management.get_device_row(GUID) == row

    def test_missing_template_file_gets_a_key_but_no_hash(self, conn):
        conn.execute(
            "CREATE TABLE devices(guid TEXT PRIMARY KEY, template_path TEXT, name TEXT, hidden BOOLEAN DEFAULT 0)"
        )
        conn.execute(
            "INSERT INTO devices VALUES (?, ?, 'x', 0)", (GUID, "/nowhere/gone.svg")
        )
        conn.commit()
        db_device_management.create_new_db_if_not_exist()
        row = db_device_management.get_device_row(GUID)
        assert row.template_key == "user:/nowhere/gone.svg"
        assert row.template_hash is None


class TestDBDeviceManagement:
    def test_template_path_writes_keep_identity_columns_in_step(self, fresh):
        db_device_management.add_update_device_template_path(GUID, str(STARTER))
        row = db_device_management.get_device_row(GUID)
        assert row.template_path == str(STARTER)
        assert row.template_key == "bundled:Starter Template.svg"
        assert db_device_management.get_device_template_path(GUID) == str(STARTER)
        assert db_device_management.get_devices_for_template_key(
            "bundled:Starter Template.svg"
        ) == [GUID]
        # The old "clear" idiom (empty path) clears all three columns
        db_device_management.add_update_device_template_path(GUID, "")
        row = db_device_management.get_device_row(GUID)
        assert (row.template_path, row.template_key, row.template_hash) == (
            None,
            None,
            None,
        )
        db_device_management.add_update_device_template_path(GUID, str(STARTER))
        db_device_management.remove_template_path_from_device(GUID)
        assert db_device_management.get_device_row(GUID).template_key is None

    def test_kind_writes_keep_hidden_in_sync(self, fresh):
        db_device_management.set_device_kind(GUID, KIND_OTHER, KIND_SOURCE_USER, "user")
        assert db_device_management.is_device_hidden(GUID)
        assert db_device_management.get_hidden_devices() == [(GUID, None)]
        db_device_management.set_device_kind(
            GUID, "other", KIND_SOURCE_AUTO, "nothing_bound"
        )
        assert db_device_management.is_device_hidden(GUID)
        db_device_management.set_device_kind(GUID, "joystick", KIND_SOURCE_USER, "user")
        assert not db_device_management.is_device_hidden(GUID)
        assert db_device_management.get_device_kind(GUID) == (
            "joystick",
            KIND_SOURCE_USER,
            "user",
        )

    def test_legacy_hidden_api_maps_to_kind(self, fresh):
        db_device_management.set_device_hidden(GUID, "Keyboard", True)
        assert db_device_management.get_device_kind(GUID) == (
            KIND_OTHER,
            KIND_SOURCE_USER,
            "user",
        )
        assert db_device_management.get_hidden_devices() == [(GUID, "Keyboard")]
        db_device_management.set_device_hidden(GUID, "Keyboard", False)
        assert db_device_management.get_device_kind(GUID) == (None, None, None)
        assert not db_device_management.is_device_hidden(GUID)
        # Unhiding a device with a user "joystick" kind keeps that kind
        db_device_management.set_device_kind(GUID_2, "joystick", KIND_SOURCE_USER, "u")
        db_device_management.set_device_hidden(GUID_2, "Stick", False)
        assert db_device_management.get_device_kind(GUID_2)[0] == "joystick"

    def test_seen_and_games(self, fresh):
        db_device_management.set_device_seen(
            GUID, "Stick", "2026-10-25T09:41:00+00:00", {"DCS World": 12}
        )
        row = db_device_management.get_device_row(GUID)
        assert row.last_seen == "2026-10-25T09:41:00+00:00"
        assert row.games == {"DCS World": 12}
        assert row.name == "Stick"
        rows = db_device_management.get_all_device_rows()
        assert [r.guid for r in rows] == [GUID]


class TestDeviceService:
    def test_user_kind_is_never_overwritten_by_auto(self, fresh):
        service = DeviceService()
        assert service.set_auto_kind(GUID, KIND_OTHER, "nothing_bound")
        assert service.kind(GUID).source == KIND_SOURCE_AUTO
        assert service.is_hidden(GUID) and service.get_all_hidden() == {GUID: GUID}
        service.clear_auto_kind(GUID)
        assert service.kind(GUID) is None and not service.is_hidden(GUID)

        service.set_make_diagram(GUID, False, "Keyboard")
        kind = service.kind(GUID)
        assert kind.is_user and kind.no_diagram
        assert not service.set_auto_kind(GUID, KIND_OTHER, "nothing_bound")
        service.clear_auto_kind(GUID)  # no-op for a user value
        assert service.kind(GUID).is_user

        service.set_make_diagram(GUID, True)
        assert service.kind(GUID).kind == KIND_JOYSTICK
        assert not service.is_hidden(GUID)
        service.set_user_kind(GUID, None)
        assert service.kind(GUID) is None

    def test_legacy_hidden_api_and_custom_names_still_work(self, fresh):
        service = DeviceService()
        service.set_hidden(GUID, "Keyboard", True)
        assert service.is_hidden(GUID)
        assert service.get_all_hidden() == {GUID: "Keyboard"}
        assert DeviceService().is_hidden(GUID)  # persisted
        service.set_hidden(GUID, "Keyboard", False)
        assert not service.is_hidden(GUID)
        service.set_custom_name(GUID, "My stick")
        assert service.resolve_name(GUID, "Stick") == "My stick"
        assert service.get_custom_name(GUID_2) is None
        service.set_custom_name(GUID, None)
        assert service.resolve_name(GUID, "Stick") == "Stick"

    def test_template_reads_through_direct_writes(self, fresh):
        service = DeviceService()
        # Old UI code writes the path straight to the table.
        db_device_management.add_update_device_template_path(GUID, str(STARTER))
        ref = service.template(GUID)
        assert ref.path == str(STARTER)
        assert ref.key == "bundled:Starter Template.svg"
        assert ref.content_hash and len(ref.content_hash) == 64
        assert service.devices_using_template("bundled:Starter Template.svg") == [GUID]
        assert set(service.devices_with_template()) == {GUID}
        service.clear_template(GUID)
        assert service.template(GUID) is None
        service.set_template(GUID_2, STARTER)
        assert service.template(GUID_2).key == "bundled:Starter Template.svg"

    def test_record_seen_and_copy_kind(self, fresh):
        service = DeviceService()
        service.record_seen(
            GUID, "Stick", "2026-10-25T09:41:00+00:00", {"DCS World": 2}
        )
        assert service.last_seen(GUID) == "2026-10-25T09:41:00+00:00"
        assert service.games(GUID) == {"DCS World": 2}
        assert service.games(GUID_2) == {}
        service.set_user_kind(GUID, KIND_OTHER, "user")
        service.copy_kind(GUID, GUID_2)
        assert service.kind(GUID_2) == service.kind(GUID)
        assert service.row(GUID_2).hidden
