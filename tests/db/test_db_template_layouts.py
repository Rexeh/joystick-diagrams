"""Layout persistence and LayoutService (in-memory sqlite): cache, write-through, drift."""

import sqlite3
from unittest.mock import patch

import pytest

from joystick_diagrams.db import db_template_layouts
from joystick_diagrams.db.layout_service import LayoutService
from joystick_diagrams.render.layout import (
    TEMPLATE_LAYER,
    HideOp,
    LayoutDocument,
    MoveOp,
)

KEY = "bundled:Starter Template.svg"


@pytest.fixture(autouse=True)
def mock_connection():
    conn = sqlite3.connect(":memory:")
    with patch(
        "joystick_diagrams.db.db_template_layouts.connection", return_value=conn
    ):
        db_template_layouts.create_new_db_if_not_exist()
        yield conn
    conn.close()


class TestDBTemplateLayouts:
    def test_upsert_get_delete_by_composite_key(self):
        db_template_layouts.upsert_layout(KEY, "", "{}", "h1")
        db_template_layouts.upsert_layout(KEY, "dcs_p1", '{"ops": []}', "h1")
        db_template_layouts.upsert_layout(KEY, "", '{"a": 1}', "h2")  # replaces
        rows = db_template_layouts.get_all_layouts()
        assert [(r[0], r[1], r[2], r[3], r[4]) for r in rows] == [
            (KEY, "", "", '{"a": 1}', "h2"),
            (KEY, "", "dcs_p1", '{"ops": []}', "h1"),
        ]
        assert rows[0][5]  # updated_at
        assert db_template_layouts.get_layout(KEY, "dcs_p1")[3] == '{"ops": []}'
        db_template_layouts.delete_layout(KEY, "")
        assert db_template_layouts.get_layout(KEY, "") is None
        db_template_layouts.rename_template_key(KEY, "user:/x.svg")
        assert db_template_layouts.get_layout("user:/x.svg", "dcs_p1") is not None
        db_template_layouts.delete_layouts_for_template("user:/x.svg")
        assert db_template_layouts.get_all_layouts() == []


class TestLayoutService:
    def test_append_get_layers_and_cache_write_through(self):
        service = LayoutService()
        move = service.append_op(
            KEY, TEMPLATE_LAYER, MoveOp(target="button_1", dx=1, dy=2), "h1"
        )
        hide = service.append_op(KEY, "dcs_p1", HideOp(target="button_2"), "h1")
        layers = service.get_layers(KEY, "dcs_p1")
        assert [op.uid for op in layers.all_ops()] == [move.uid, hide.uid]
        assert (
            layers.template.content_hash == "h1"
            and layers.profile.profile_key == "dcs_p1"
        )
        assert service.has_ops(KEY, None) and not service.has_ops("other", "dcs_p1")
        assert service.get_layers(KEY, None).profile.is_empty
        # A fresh service reads the same rows back from the database.
        reloaded = LayoutService()
        assert [op.uid for op in reloaded.get_layers(KEY, "dcs_p1").all_ops()] == [
            move.uid,
            hide.uid,
        ]
        assert reloaded.templates_with_layouts() == {KEY}
        # Documents handed out are copies: editing them does not touch the cache.
        doc = service.get_document(KEY)
        doc.ops.clear()
        assert not service.get_document(KEY).is_empty

    def test_coalesce_replace_remove_clear(self):
        service = LayoutService()
        first = service.append_op(
            KEY, "", MoveOp(target="button_1", dx=1, dy=0), "h", coalesce=True
        )
        merged = service.append_op(
            KEY, "", MoveOp(target="button_1", dx=2, dy=2), "h", coalesce=True
        )
        assert merged.uid == first.uid and len(service.get_document(KEY).ops) == 1
        assert service.replace_op(
            KEY, "", first.uid, HideOp(target="button_1", uid=first.uid), "h"
        )
        assert isinstance(service.get_document(KEY).ops[0], HideOp)
        assert not service.replace_op(KEY, "", "missing", HideOp(target="x"), "h")
        assert service.remove_op(KEY, "", first.uid)
        assert service.get_document(KEY).is_empty  # empty list deletes the row
        assert db_template_layouts.get_layout(KEY, "") is None
        service.append_op(KEY, "p", HideOp(target="button_1"), "h")
        service.clear_template(KEY)
        assert not service.has_ops(KEY, "p")

    def test_invalid_rows_are_skipped(self):
        db_template_layouts.upsert_layout(KEY, "", '{"ops": [{"op": "nope"}]}', "h")
        db_template_layouts.upsert_layout(
            KEY, "ok", LayoutDocument(ops=[HideOp(target="b")]).model_dump_json(), "h"
        )
        service = LayoutService()
        assert service.get_document(KEY).is_empty
        assert not service.get_document(KEY, "ok").is_empty

    def test_drift_and_relink(self):
        service = LayoutService()
        service.append_op(KEY, "", MoveOp(target="button_1", dx=1, dy=1), "hash-A")
        assert not service.drift_notice(KEY, None, "hash-A")
        assert service.drift_notice(KEY, None, "hash-B")
        assert not service.drift_notice(KEY, None, None)
        assert service.relink_candidates("hash-A") == [KEY]
        assert service.relink_candidates("hash-B") == []
        service.relink(KEY, "user:/moved.svg")
        assert not service.has_ops(KEY, None)
        assert service.get_document("user:/moved.svg").template_key == "user:/moved.svg"
        assert db_template_layouts.get_layout("user:/moved.svg", "") is not None

    def test_snapshot_is_immutable_and_keyed_by_layer(self):
        service = LayoutService()
        service.append_op(KEY, "", MoveOp(target="button_1", dx=1, dy=1), "h")
        snapshot = service.snapshot()
        assert set(snapshot) == {(KEY, "", "")}
        with pytest.raises(TypeError):
            snapshot[("x", "", "")] = LayoutDocument()
        assert (
            service.stored_hash(KEY, "") == "h"
            and service.stored_hash(KEY, "p") is None
        )


GUID_A = "666ec0a0-556b-11ee-8002-444553540000"
GUID_B = "777ec0a0-556b-11ee-8002-444553540000"


class TestDeviceKeyedLayouts:
    def test_rows_are_keyed_by_device_guid_too(self):
        db_template_layouts.upsert_layout(KEY, "", "{}", "h", device_guid=GUID_A)
        db_template_layouts.upsert_layout(KEY, "", '{"a": 1}', "h")  # shared layer
        assert db_template_layouts.get_layout(KEY, "", GUID_A)[3] == "{}"
        assert db_template_layouts.get_layout(KEY, "")[3] == '{"a": 1}'
        assert db_template_layouts.get_layout(KEY, "", GUID_B) is None
        assert db_template_layouts.copy_device_layers(KEY, GUID_A, GUID_B) == 1
        assert db_template_layouts.get_layout(KEY, "", GUID_B)[3] == "{}"
        db_template_layouts.delete_layouts_for_template(KEY, GUID_A)
        assert db_template_layouts.get_layout(KEY, "", GUID_A) is None
        assert len(db_template_layouts.get_all_layouts()) == 2
        db_template_layouts.delete_layout(KEY, "", GUID_B)
        assert len(db_template_layouts.get_all_layouts()) == 1

    def test_legacy_rows_migrate_to_every_device_using_the_template(
        self, mock_connection
    ):
        conn = mock_connection
        conn.execute("DROP TABLE template_layouts")
        conn.execute(
            "CREATE TABLE template_layouts(template_key TEXT NOT NULL, "
            "profile_key TEXT NOT NULL DEFAULT '', ops_json TEXT NOT NULL, "
            "content_hash TEXT, updated_at TEXT, PRIMARY KEY (template_key, profile_key))"
        )
        conn.execute(
            "INSERT INTO template_layouts VALUES (?, '', '{}', 'h', 't1')", (KEY,)
        )
        conn.execute(
            "INSERT INTO template_layouts VALUES (?, 'dcs_p1', '{\"x\": 1}', 'h', 't2')",
            (KEY,),
        )
        conn.execute(
            "INSERT INTO template_layouts VALUES ('user:/orphan.svg', '', '{}', 'h', 't3')"
        )
        # The devices table (migrated first by db_handler) says who uses the template.
        conn.execute("CREATE TABLE devices(guid TEXT PRIMARY KEY, template_key TEXT)")
        conn.execute("INSERT INTO devices VALUES (?, ?)", (GUID_A, KEY))
        conn.execute("INSERT INTO devices VALUES (?, ?)", (GUID_B, KEY))
        conn.commit()

        db_template_layouts.create_new_db_if_not_exist()

        rows = {
            (r[0], r[1], r[2]): (r[3], r[5])
            for r in db_template_layouts.get_all_layouts()
        }
        assert rows == {
            (KEY, GUID_A, ""): ("{}", "t1"),
            (KEY, GUID_B, ""): ("{}", "t1"),
            (KEY, GUID_A, "dcs_p1"): ('{"x": 1}', "t2"),
            (KEY, GUID_B, "dcs_p1"): ('{"x": 1}', "t2"),
            # nobody uses this template: kept as the shared layer
            ("user:/orphan.svg", "", ""): ("{}", "t3"),
        }
        assert not conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'template_layouts_legacy'"
        ).fetchone()
        db_template_layouts.create_new_db_if_not_exist()  # idempotent
        assert len(db_template_layouts.get_all_layouts()) == 5

    def test_legacy_rows_without_a_devices_table_become_shared_layers(
        self, mock_connection
    ):
        conn = mock_connection
        conn.execute("DROP TABLE template_layouts")
        conn.execute(
            "CREATE TABLE template_layouts(template_key TEXT NOT NULL, "
            "profile_key TEXT NOT NULL DEFAULT '', ops_json TEXT NOT NULL, "
            "content_hash TEXT, updated_at TEXT, PRIMARY KEY (template_key, profile_key))"
        )
        conn.execute(
            "INSERT INTO template_layouts VALUES (?, '', '{}', 'h', 't1')", (KEY,)
        )
        conn.commit()
        db_template_layouts.create_new_db_if_not_exist()
        assert [(r[0], r[1], r[2]) for r in db_template_layouts.get_all_layouts()] == [
            (KEY, "", "")
        ]

    def test_service_prefers_a_controllers_own_layer_and_falls_back_to_shared(self):
        service = LayoutService()
        shared = service.append_op(KEY, "", MoveOp(target="button_1", dx=1, dy=1), "h")
        own = service.append_op(
            KEY, "", HideOp(target="button_1"), "h", device_guid=GUID_A
        )
        profile_shared = service.append_op(
            KEY, "dcs_p1", HideOp(target="button_2"), "h"
        )
        # A: own template layer, shared profile layer
        layers = service.get_layers(KEY, "dcs_p1", GUID_A)
        assert [op.uid for op in layers.all_ops()] == [own.uid, profile_shared.uid]
        assert layers.template.device_guid == GUID_A
        # B: nothing of its own → both from the shared rows
        layers_b = service.get_layers(KEY, "dcs_p1", GUID_B)
        assert [op.uid for op in layers_b.all_ops()] == [shared.uid, profile_shared.uid]
        assert service.has_ops(KEY, None, GUID_B)
        # Exact-row reads do not fall back
        assert service.get_document(KEY, "", GUID_B).is_empty
        assert service.stored_hash(KEY, "", GUID_A) == "h"
        assert service.stored_hash(KEY, "", GUID_B) is None
        assert service.layers_of_template(KEY) == ["", "dcs_p1"]
        assert service.layers_of_template(KEY, GUID_A) == [""]
        assert service.devices_of_template(KEY) == ["", GUID_A]
        assert set(service.snapshot()) == {
            (KEY, "", ""),
            (KEY, GUID_A, ""),
            (KEY, "", "dcs_p1"),
        }
        # Reloaded from the database with the same keys
        assert set(LayoutService().snapshot()) == set(service.snapshot())

    def test_service_writes_edit_only_the_addressed_controller(self):
        service = LayoutService()
        service.append_op(KEY, "", MoveOp(target="button_1", dx=1, dy=1), "h")
        op_a = service.append_op(
            KEY, "", MoveOp(target="button_2", dx=1, dy=1), "h", device_guid=GUID_A
        )
        assert service.replace_op(
            KEY,
            "",
            op_a.uid,
            HideOp(target="button_2", uid=op_a.uid),
            "h",
            device_guid=GUID_A,
        )
        assert isinstance(service.get_document(KEY, "", GUID_A).ops[0], HideOp)
        assert not service.remove_op(KEY, "", op_a.uid)  # not in the shared layer
        assert service.remove_op(KEY, "", op_a.uid, device_guid=GUID_A)
        assert service.get_document(KEY, "", GUID_A).is_empty
        assert not service.get_document(KEY).is_empty
        service.append_op(KEY, "p", HideOp(target="b"), "h", device_guid=GUID_A)
        service.append_op(KEY, "p", HideOp(target="b"), "h", device_guid=GUID_B)
        service.clear_template(KEY, GUID_A)
        assert service.layers_of_template(KEY, GUID_A) == []
        assert service.layers_of_template(KEY, GUID_B) == ["p"]
        service.clear(KEY, "p", device_guid=GUID_B)
        assert service.layers_of_template(KEY) == [""]

    def test_copy_device_layers_and_drift_per_controller(self):
        service = LayoutService()
        service.append_op(
            KEY, "", MoveOp(target="b", dx=1, dy=1), "hash-A", device_guid=GUID_A
        )
        service.append_op(KEY, "p", HideOp(target="b"), "hash-A", device_guid=GUID_A)
        assert service.copy_device_layers(KEY, GUID_A, GUID_B) == 2
        assert (
            service.get_layers(KEY, "p", GUID_B).all_ops()
            == service.get_layers(KEY, "p", GUID_A).all_ops()
        )
        assert service.get_document(KEY, "p", GUID_B).device_guid == GUID_B
        assert LayoutService().has_ops(KEY, "p", GUID_B)
        assert service.drift_notice(KEY, "p", "hash-B", GUID_B)
        assert not service.drift_notice(KEY, "p", "hash-A", GUID_B)
        assert not service.drift_notice(KEY, "p", "hash-B")  # nothing stored as shared
        service.relink(KEY, "user:/moved.svg")
        assert service.has_ops("user:/moved.svg", "p", GUID_A)
        assert not service.has_ops(KEY, "p", GUID_A)
