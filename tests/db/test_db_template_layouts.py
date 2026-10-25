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
        assert [(r[0], r[1], r[2], r[3]) for r in rows] == [
            (KEY, "", '{"a": 1}', "h2"),
            (KEY, "dcs_p1", '{"ops": []}', "h1"),
        ]
        assert rows[0][4]  # updated_at
        assert db_template_layouts.get_layout(KEY, "dcs_p1")[2] == '{"ops": []}'
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
        assert set(snapshot) == {(KEY, "")}
        with pytest.raises(TypeError):
            snapshot[("x", "")] = LayoutDocument()
        assert (
            service.stored_hash(KEY, "") == "h"
            and service.stored_hash(KEY, "p") is None
        )
