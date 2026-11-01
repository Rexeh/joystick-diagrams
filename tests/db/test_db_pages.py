"""Pages persistence and PageService (in-memory sqlite)."""

import sqlite3
from unittest.mock import patch

import pytest

from joystick_diagrams.db import db_pages
from joystick_diagrams.db.page_service import PageService, copy_name
from joystick_diagrams.render.page import (
    Arrangement,
    Orientation,
    Page,
    PageNote,
    Placement,
    SizePreset,
    validate_page,
)

VKB = "a1b2c3d4-0001-11ee-8001-444553540000"
THROTTLE = "a1b2c3d4-0002-11ee-8002-444553540000"
VIRPIL = "a1b2c3d4-0003-11ee-8003-444553540000"


@pytest.fixture(autouse=True)
def mock_connection():
    conn = sqlite3.connect(":memory:")
    with patch("joystick_diagrams.db.db_pages.connection", return_value=conn):
        db_pages.create_new_db_if_not_exist()
        yield conn
    conn.close()


def _record(page_id="p1", name="Stick + Throttle", **overrides) -> db_pages.PageRecord:
    fields = {
        "page_id": page_id,
        "name": name,
        "size_preset": "a4",
        "width_mm": None,
        "height_mm": None,
        "orientation": "auto",
        "arrangement": "side_by_side",
        "placements_json": '[{"device_guid": "%s"}, {"device_guid": "%s"}]'
        % (VKB, THROTTLE),
        "ops_json": "{}",
        "export_members_separately": False,
    }
    fields.update(overrides)
    return db_pages.PageRecord(**fields)


class TestDBPages:
    def test_upsert_get_delete(self):
        stamp = db_pages.upsert_page(_record())
        assert stamp
        db_pages.upsert_page(_record(name="Kneeboard", export_members_separately=True))
        rows = db_pages.get_all_pages()
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == "p1" and row[1] == "Kneeboard"
        assert row[9] == 1  # export_members_separately stored as INTEGER
        assert row[10]  # updated_at
        assert db_pages.get_page("p1") == row
        assert db_pages.get_page("nope") is None
        db_pages.delete_page("p1")
        assert db_pages.get_all_pages() == []

    def test_profile_rule_round_trips_and_defaults_to_shared(self):
        db_pages.upsert_page(_record())
        assert db_pages.get_page("p1")[11] == "shared"
        db_pages.upsert_page(_record(profile_rule="any"))
        assert db_pages.get_page("p1")[11] == "any"
        assert PageService().get("p1").profile_rule.value == "any"

    def test_older_tables_gain_the_column_with_the_shared_default(self):
        old = sqlite3.connect(":memory:")
        old.execute(
            "CREATE TABLE pages(page_id TEXT PRIMARY KEY, name TEXT NOT NULL, "
            "size_preset TEXT NOT NULL, width_mm REAL, height_mm REAL, "
            "orientation TEXT NOT NULL, arrangement TEXT NOT NULL, "
            "placements_json TEXT NOT NULL, ops_json TEXT NOT NULL, "
            "export_members_separately INTEGER NOT NULL DEFAULT 0, updated_at TEXT)"
        )
        old.execute(
            "INSERT INTO pages VALUES ('old', 'Old page', 'a4', NULL, NULL, 'auto', "
            "'side_by_side', ?, '{}', 0, NULL)",
            ('[{"device_guid": "%s"}, {"device_guid": "%s"}]' % (VKB, THROTTLE),),
        )
        old.commit()
        with patch("joystick_diagrams.db.db_pages.connection", return_value=old):
            db_pages.create_new_db_if_not_exist()
            db_pages.create_new_db_if_not_exist()  # idempotent
            assert db_pages.get_page("old")[11] == "shared"
            assert PageService().get("old").profile_rule.value == "shared"
        old.close()


class TestValidation:
    def test_needs_two_distinct_members(self):
        one = Page(name="One", placements=[Placement(device_guid=VKB)])
        assert any("2 different" in p for p in validate_page(one))
        dupes = Page(
            name="Dupes",
            placements=[Placement(device_guid=VKB), Placement(device_guid=VKB)],
        )
        assert any("2 different" in p for p in validate_page(dupes))
        fine = Page(
            name="Fine",
            placements=[Placement(device_guid=VKB), Placement(device_guid=THROTTLE)],
        )
        assert validate_page(fine) == []

    def test_other_rules(self):
        base = dict(
            placements=[Placement(device_guid=VKB), Placement(device_guid=THROTTLE)]
        )
        assert any("name" in p for p in validate_page(Page(name="  ", **base)))
        custom = Page(name="C", size_preset=SizePreset.CUSTOM, **base)
        assert any("custom" in p.lower() for p in validate_page(custom))
        assert (
            validate_page(custom.model_copy(update={"width_mm": 100, "height_mm": 50}))
            == []
        )
        assert any(
            "Scale" in p for p in validate_page(Page(name="S", scale=0.01, **base))
        )
        assert any(
            "negative" in p for p in validate_page(Page(name="G", gap_mm=-1, **base))
        )


class TestPageService:
    def test_create_persists_and_reloads(self):
        service = PageService()
        page = service.create(
            "Stick + Throttle",
            [VKB, THROTTLE],
            arrangement=Arrangement.STACKED,
            size_preset=SizePreset.KNEEBOARD,
            scale=0.9,
            gap_mm=4,
            export_members_separately=True,
        )
        assert page.page_id.startswith("page_")
        assert page.updated_at
        assert page.member_guids == [VKB, THROTTLE]

        reloaded = PageService()
        again = reloaded.get(page.page_id)
        assert again == page
        assert again.arrangement is Arrangement.STACKED
        assert again.size_preset is SizePreset.KNEEBOARD
        assert again.scale == 0.9 and again.gap_mm == 4
        assert again.export_members_separately is True
        assert reloaded.pages() == [page]

    def test_validation_errors_are_value_errors(self):
        service = PageService()
        with pytest.raises(ValueError, match="2 different"):
            service.create("Solo", [VKB])
        service.create("Taken", [VKB, THROTTLE])
        with pytest.raises(ValueError, match="already exists"):
            service.create("  taken ", [VKB, VIRPIL])
        assert len(service.pages()) == 1

    def test_rename_duplicate_delete(self):
        service = PageService()
        page = service.create("Stick + Throttle", [VKB, THROTTLE])
        renamed = service.rename(page.page_id, "  Kneeboard  ")
        assert renamed.name == "Kneeboard"
        copy = service.duplicate(page.page_id)
        assert copy.page_id != page.page_id
        assert copy.name == "Kneeboard copy"
        assert copy.member_guids == [VKB, THROTTLE]
        second = service.duplicate(page.page_id)
        assert second.name == "Kneeboard copy 2"
        service.delete(copy.page_id)
        assert [p.name for p in service.pages()] == ["Kneeboard", "Kneeboard copy 2"]
        assert [r[1] for r in db_pages.get_all_pages()] == [
            "Kneeboard",
            "Kneeboard copy 2",
        ]

    def test_members_and_lookups(self):
        service = PageService()
        a = service.create("A", [VKB, THROTTLE], export_members_separately=True)
        b = service.create("B", [VKB, VIRPIL])
        assert [p.name for p in service.pages_for_device(VKB)] == ["A", "B"]
        assert service.pages_for_device(THROTTLE) == [a]
        assert service.member_guids() == {VKB, THROTTLE, VIRPIL}
        assert service.members_exported_separately() == {VKB, THROTTLE}
        changed = service.set_members(b.page_id, [VIRPIL, THROTTLE])
        assert changed.member_guids == [VIRPIL, THROTTLE]

    def test_remove_member_drops_or_deletes_pages(self):
        service = PageService()
        a = service.create("A", [VKB, THROTTLE])
        b = service.create("B", [VKB, THROTTLE, VIRPIL])
        changed = service.remove_member(THROTTLE)
        assert set(changed) == {a.page_id, b.page_id}
        assert service.get(a.page_id) is None  # fell below 2 members
        assert service.get(b.page_id).member_guids == [VKB, VIRPIL]
        assert len(db_pages.get_all_pages()) == 1

    def test_arrange_clears_positions_and_add_note(self):
        service = PageService()
        page = service.create("A", [VKB, THROTTLE])
        moved = page.model_copy(
            update={
                "placements": [
                    Placement(device_guid=VKB, x_mm=10, y_mm=20, scale=0.8),
                    Placement(device_guid=THROTTLE),
                ]
            }
        )
        service.save(moved)
        arranged = service.arrange(
            page.page_id,
            Arrangement.GRID,
            size_preset=SizePreset.LETTER,
            orientation=Orientation.PORTRAIT,
        )
        assert arranged.arrangement is Arrangement.GRID
        assert arranged.size_preset is SizePreset.LETTER
        assert arranged.orientation is Orientation.PORTRAIT
        assert arranged.placements[0].x_mm is None
        assert arranged.placements[0].scale == 0.8  # scale survives re-arranging
        noted = service.add_note(page.page_id, PageNote(text="Gear: G", x_mm=5, y_mm=5))
        assert [n.text for n in PageService().get(page.page_id).notes] == ["Gear: G"]
        assert noted.notes[0].x_mm == 5

    def test_invalid_rows_are_skipped(self):
        db_pages.upsert_page(_record(page_id="bad", placements_json="not json"))
        db_pages.upsert_page(_record(page_id="worse", size_preset="a9"))
        db_pages.upsert_page(_record(page_id="good"))
        service = PageService()
        assert [p.page_id for p in service.pages()] == ["good"]

    def test_copy_name(self):
        assert copy_name("A", set()) == "A copy"
        assert copy_name("A", {"a copy"}) == "A copy 2"
