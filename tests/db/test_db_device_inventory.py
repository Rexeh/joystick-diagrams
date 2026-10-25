"""Inventory snapshot: stamps, "new since last read", auto kinds, GUID inheritance."""

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from joystick_diagrams.db import (
    db_device_inventory,
    db_device_management,
    db_template_layouts,
)
from joystick_diagrams.db.device_inventory_service import (
    NOTICE_KEPT_TEMPLATE,
    NOTICE_POSSIBLE_DUPLICATE,
    DeviceInventoryService,
    normalise_device_name,
)
from joystick_diagrams.db.device_service import DeviceService
from joystick_diagrams.db.layout_service import LayoutService
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.render.layout import HideOp, MoveOp

OLD = "666ec0a0-556b-11ee-8002-444553540000"
NEW = "777ec0a0-556b-11ee-8002-444553540000"
OTHER = "888ec0a0-556b-11ee-8002-444553540000"
TEST_TEMPLATE = Path("tests/data/template_test.svg")
T1 = datetime(2026, 10, 25, 9, 41, tzinfo=timezone.utc)
T2 = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)
T3 = datetime(2026, 10, 25, 11, 0, tzinfo=timezone.utc)

DB_MODULES = (db_device_management, db_template_layouts, db_device_inventory)


class Origin:
    def __init__(self, name):
        self.name = name


class FakeWrapper:
    def __init__(self, profile: Profile_, game="DCS World"):
        self.original_profile = profile
        self.profile = profile
        self.profile_origin = Origin(game)
        self.profile_key = f"{game.lower()}_{profile.name.lower()}"


@pytest.fixture(autouse=True)
def memory_db():
    conn = sqlite3.connect(":memory:")
    patches = [
        patch(f"{module.__name__}.connection", return_value=conn)
        for module in DB_MODULES
    ]
    for p in patches:
        p.start()
    for module in DB_MODULES:
        module.create_new_db_if_not_exist()
    yield conn
    for p in patches:
        p.stop()
    conn.close()


@pytest.fixture
def services():
    device_service = DeviceService()
    layout_service = LayoutService()
    return (
        device_service,
        layout_service,
        DeviceInventoryService(device_service, layout_service),
    )


def wrapper(guid, name, profile="F-16C", game="DCS World", *buttons):
    p = Profile_(profile)
    device = p.add_device(guid, name)
    for number in buttons or (1,):
        device.create_input(Button(number), f"Action {number}")
    return FakeWrapper(p, game)


def test_normalise_device_name_strips_guid_whitespace_and_case():
    assert normalise_device_name("  Gladiator   NXT ") == "gladiator nxt"
    assert (
        normalise_device_name("VKB Gladiator {666EC0A0-556B-11EE-8002-444553540000}")
        == "vkb gladiator"
    )
    assert (
        normalise_device_name("T.16000M 666ec0a0-556b-11ee-8002-444553540000")
        == "t.16000m"
    )
    assert normalise_device_name("") is None and normalise_device_name(None) is None


class TestDBDeviceInventory:
    def test_record_seen_keeps_first_seen_and_counts_reads(self):
        db_device_inventory.record_seen(OLD, "Stick", "stick", "t1")
        db_device_inventory.record_seen(OLD, None, None, "t2")
        row = db_device_inventory.get_row(OLD)
        assert (row.first_seen, row.last_seen, row.read_count) == ("t1", "t2", 2)
        assert row.name == "Stick" and row.normalised_name == "stick"
        db_device_inventory.set_notices(OLD, "[]")
        assert db_device_inventory.get_row(OLD).notices_json == "[]"
        assert [r.guid for r in db_device_inventory.get_all_rows()] == [OLD]
        db_device_inventory.delete_row(OLD)
        assert db_device_inventory.get_row(OLD) is None


class TestRecordRead:
    def test_stamps_games_and_new_since_last_read(self, services):
        device_service, _layouts, inventory = services
        first = inventory.record_read(
            [
                wrapper(OLD, "Stick"),
                wrapper(OLD, "Stick", "Mirage"),
                wrapper(OLD, "Stick", "Ship", "Star Citizen"),
            ],
            now=T1,
        )
        assert first.seen == [OLD] and first.new == [OLD]
        assert inventory.is_new(OLD) and inventory.new_guids() == [OLD]
        assert device_service.last_seen(OLD) == T1.isoformat()
        assert device_service.games(OLD) == {"DCS World": 2, "Star Citizen": 1}
        assert inventory.latest_read() == T1.isoformat()

        second = inventory.record_read(
            [wrapper(OLD, "Stick"), wrapper(OTHER, "Pedals")], now=T2
        )
        assert second.new == [OTHER] and second.seen == [OLD, OTHER]
        assert not inventory.is_new(OLD) and inventory.is_new(OTHER)
        assert inventory.entry(OLD).read_count == 2
        assert inventory.known_guids() == [OLD, OTHER]
        # A fresh service reads the same rows back
        assert DeviceInventoryService(device_service, _layouts).is_new(OTHER)

    def test_auto_kinds_are_recomputed_and_never_touch_user_values(self, services):
        device_service, _layouts, inventory = services
        empty = Profile_("Gremlin")
        empty.add_device(OTHER, "vJoy Device")
        result = inventory.record_read(
            [
                wrapper(OLD, "Keyboard", game="Joystick Gremlin"),
                FakeWrapper(empty, "Joystick Gremlin"),
            ],
            now=T1,
        )
        # Only "nothing bound" is automatic; a keyboard with bindings is a controller
        assert result.auto_kinds == {OTHER: ("other", "nothing_bound")}
        assert device_service.is_hidden(OTHER) and not device_service.is_hidden(OLD)
        # Next read: the vJoy device now has bindings → automatic value cleared
        inventory.record_read([wrapper(OTHER, "vJoy Device")], now=T2)
        assert device_service.kind(OTHER) is None and not device_service.is_hidden(
            OTHER
        )
        # A user choice survives any read: the user wants a diagram for vJoy
        device_service.set_make_diagram(OTHER, True)
        empty_again = Profile_("Gremlin")
        empty_again.add_device(OTHER, "vJoy Device")
        result = inventory.record_read(
            [FakeWrapper(empty_again, "Joystick Gremlin")], now=T3
        )
        assert OTHER not in result.auto_kinds
        assert device_service.kind(OTHER).kind == "joystick"


class TestGuidInheritance:
    def seed_old(self, services, tmp_path):
        device_service, layout_service, inventory = services
        template = tmp_path / "Gladiator.svg"
        shutil.copy(TEST_TEMPLATE, template)
        inventory.record_read([wrapper(OLD, "VKB Gladiator NXT")], now=T1)
        ref = device_service.set_template(OLD, template)
        device_service.set_user_kind(OLD, "joystick", "user")
        layout_service.append_op(
            ref.key, "", MoveOp(target="button_1", dx=1, dy=1), "h", device_guid=OLD
        )
        layout_service.append_op(
            ref.key, "dcs world_f-16c", HideOp(target="button_2"), "h", device_guid=OLD
        )
        return ref

    def test_new_guid_with_the_same_name_keeps_template_kind_and_layouts(
        self, services, tmp_path
    ):
        device_service, layout_service, inventory = services
        ref = self.seed_old(services, tmp_path)
        result = inventory.record_read(
            [wrapper(NEW, "VKB  Gladiator NXT {777EC0A0-556B-11EE-8002-444553540000}")],
            now=T2,
        )
        assert result.new == [NEW]
        assert [n.code for n in result.notices] == [NOTICE_KEPT_TEMPLATE]
        notice = result.inherited[0]
        assert notice.guid == NEW and notice.related_guid == OLD
        assert (
            notice.text == "Kept your template: this controller came back with a new ID"
        )
        assert result.duplicates == []
        assert device_service.template(NEW) == ref
        assert (
            device_service.kind(NEW).kind == "joystick"
            and device_service.kind(NEW).is_user
        )
        layers = layout_service.get_layers(ref.key, "dcs world_f-16c", NEW)
        assert [type(op).__name__ for op in layers.all_ops()] == ["MoveOp", "HideOp"]
        # The notice is stored on the row until a screen clears it
        assert [n.code for n in inventory.notices(NEW)] == [NOTICE_KEPT_TEMPLATE]
        inventory.clear_notices(NEW)
        assert inventory.notices(NEW) == []

    def test_both_guids_in_one_read_flag_a_possible_duplicate(self, services, tmp_path):
        _device_service, _layouts, inventory = services
        self.seed_old(services, tmp_path)
        result = inventory.record_read(
            [wrapper(OLD, "VKB Gladiator NXT"), wrapper(NEW, "vkb gladiator nxt")],
            now=T2,
        )
        assert [n.code for n in result.notices] == [
            NOTICE_KEPT_TEMPLATE,
            NOTICE_POSSIBLE_DUPLICATE,
        ]
        duplicate = result.duplicates[0]
        assert duplicate.related_guid == OLD
        assert (
            duplicate.text
            == "Possible duplicate: this may be the same controller as VKB Gladiator NXT"
        )

    def test_exact_match_only_and_only_from_controllers_with_a_template(
        self, services, tmp_path
    ):
        device_service, _layouts, inventory = services
        self.seed_old(services, tmp_path)
        inventory.record_read(
            [wrapper(OTHER, "Pedals")], now=T2
        )  # remembered, no template
        result = inventory.record_read(
            [
                wrapper(NEW, "VKB Gladiator NXT Mk2"),
                wrapper("999ec0a0-556b-11ee-8002-444553540000", "Pedals"),
            ],
            now=T3,
        )
        assert result.notices == []
        assert device_service.template(NEW) is None

    def test_a_guid_seen_before_never_inherits(self, services, tmp_path):
        device_service, _layouts, inventory = services
        inventory.record_read([wrapper(NEW, "VKB Gladiator NXT")], now=T1)
        self.seed_old(services, tmp_path)
        result = inventory.record_read([wrapper(NEW, "VKB Gladiator NXT")], now=T3)
        assert result.notices == [] and device_service.template(NEW) is None
        inventory.forget(NEW)
        assert inventory.entry(NEW) is None
