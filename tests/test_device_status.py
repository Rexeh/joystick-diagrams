"""``device_status``: the one classification every screen calls (in-memory sqlite)."""

import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from joystick_diagrams.conflict_strategy import AliasConflictStrategy
from joystick_diagrams.db import (
    db_device_aliases,
    db_device_inventory,
    db_device_management,
    db_template_layouts,
)
from joystick_diagrams.db.device_alias_service import DeviceAliasService
from joystick_diagrams.db.device_inventory_service import DeviceInventoryService
from joystick_diagrams.db.device_service import DeviceService
from joystick_diagrams.db.layout_service import LayoutService
from joystick_diagrams.device_status import (
    DeviceStatus,
    StatusSources,
    all_device_statuses,
    auto_classification,
    collect_device_facts,
    device_status,
    reason_text,
)
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input_routing import RouteKey, RouteTarget, apply_routes

STICK = "666ec0a0-556b-11ee-8002-444553540000"
VJOY = "777ec0a0-556b-11ee-8002-444553540000"
KEYBOARD = "888ec0a0-556b-11ee-8002-444553540000"
UNKNOWN = "999ec0a0-556b-11ee-8002-444553540000"
TEST_TEMPLATE = Path("tests/data/template_test.svg")  # BUTTON_1, BUTTON_2, BUTTON_10

DB_MODULES = (
    db_device_management,
    db_device_aliases,
    db_template_layouts,
    db_device_inventory,
)


class Origin:
    def __init__(self, name):
        self.name = name


class FakeWrapper:
    """Just the attributes ``device_status`` reads from a ``ProfileWrapper``."""

    def __init__(
        self, original: Profile_, processed: Profile_ | None, game="DCS World"
    ):
        self.original_profile = original
        self.profile = processed if processed is not None else deepcopy(original)
        self.profile_origin = Origin(game)
        self.profile_key = f"{game.lower()}_{original.name.lower()}"
        self.profile_name = original.name


@pytest.fixture(autouse=True)
def memory_db(tmp_path):
    conn = sqlite3.connect(":memory:")
    patches = [
        patch(f"{module.__name__}.connection", return_value=conn)
        for module in DB_MODULES
    ]
    patches.append(
        patch(
            "joystick_diagrams.template_identity.user_templates_root",
            return_value=tmp_path / "My templates",
        )
    )
    for p in patches:
        p.start()
    for module in DB_MODULES:
        module.create_new_db_if_not_exist()
    yield conn
    for p in patches:
        p.stop()
    conn.close()


@pytest.fixture
def sources():
    device_service = DeviceService()
    layout_service = LayoutService()
    return StatusSources(
        device_service=device_service,
        alias_service=DeviceAliasService(),
        inventory=DeviceInventoryService(device_service, layout_service),
        layout_service=layout_service,
    )


def stick_profile(name="F-16C", *buttons: int) -> Profile_:
    profile = Profile_(name)
    device = profile.add_device(STICK, "Gladiator NXT")
    for number in buttons or (1,):
        device.create_input(Button(number), f"Action {number}")
    return profile


class TestFacts:
    def test_facts_count_bound_profiles_per_game(self):
        wrappers = [
            FakeWrapper(stick_profile("F-16C"), None),
            FakeWrapper(stick_profile("Mirage"), None),
            FakeWrapper(stick_profile("Ship"), None, game="Star Citizen"),
        ]
        facts = collect_device_facts(wrappers)
        assert facts[STICK].profile_count == 3
        assert facts[STICK].games == {"DCS World": 2, "Star Citizen": 1}
        assert facts[STICK].name == "Gladiator NXT"
        assert auto_classification(facts[STICK]) is None

    def test_nothing_bound_after_routing_is_moved(self):
        original = Profile_("Gremlin")
        original.add_device(STICK, "Gladiator NXT")
        vjoy = original.add_device(VJOY, "vJoy Device")
        vjoy.create_input(Button(108), "Gear")
        original.input_routes[RouteKey(VJOY, "buttons", "BUTTON_108")] = [
            RouteTarget(STICK, "buttons", "BUTTON_1", "")
        ]
        processed = deepcopy(original)
        apply_routes(
            processed,
            dict(original.input_routes),
            AliasConflictStrategy.CONCATENATE,
            {STICK: "Gladiator NXT"},
        )
        assert VJOY not in processed.devices  # routing emptied and dropped it
        facts = collect_device_facts(
            [FakeWrapper(original, processed, "Joystick Gremlin")]
        )
        assert facts[VJOY].seen_in_read and not facts[VJOY].bound
        assert facts[VJOY].routed_away
        assert auto_classification(facts[VJOY]) == ("other", "nothing_bound_moved")
        assert facts[STICK].profile_count == 1

    def test_device_with_no_inputs_is_nothing_bound(self):
        profile = Profile_("Empty")
        profile.add_device(VJOY, "vJoy Device")
        facts = collect_device_facts([FakeWrapper(profile, None)])
        assert auto_classification(facts[VJOY]) == ("other", "nothing_bound")

    def test_mock_like_wrappers_without_profiles_are_ignored(self):
        class Odd:
            profile = None
            original_profile = object()

        assert collect_device_facts([Odd()]) == {}


class TestStatus:
    def test_no_profiles_then_not_seen_then_merged(self, sources):
        assert device_status(UNKNOWN, [], sources).state is DeviceStatus.NO_PROFILES
        sources.inventory.record_read([FakeWrapper(stick_profile(), None)])
        info = device_status(STICK, [], sources)
        assert info.state is DeviceStatus.NOT_SEEN
        assert info.reason_text == "Not in your latest bindings"
        assert info.name == "Gladiator NXT" and info.is_new
        sources.alias_service.set_alias(STICK, VJOY)
        merged = device_status(STICK, [FakeWrapper(stick_profile(), None)], sources)
        assert merged.state is DeviceStatus.MERGED and merged.merged_into == VJOY

    def test_automatic_no_diagram_reasons_and_user_override(self, sources):
        profile = Profile_("Ship")
        profile.add_device(KEYBOARD, "Keyboard")
        profile.get_device(KEYBOARD).create_input(Button(1), "Fire")
        profile.add_device(VJOY, "vJoy Device")
        wrappers = [FakeWrapper(profile, None, game="Star Citizen")]

        # A keyboard with bindings is a controller like any other: no guessing
        keyboard = device_status(KEYBOARD, wrappers, sources)
        assert keyboard.state is DeviceStatus.NEEDS_TEMPLATE
        assert keyboard.profile_count == 1

        vjoy = device_status(VJOY, wrappers, sources)
        assert vjoy.state is DeviceStatus.NO_DIAGRAM
        assert vjoy.reason_text == "Nothing bound"
        assert vjoy.kind_source == "auto"

        # The user asks for a diagram: the automatic rule no longer applies
        sources.device_service.set_make_diagram(VJOY, True)
        assert (
            device_status(VJOY, wrappers, sources).state is DeviceStatus.NEEDS_TEMPLATE
        )
        # The user says No diagram for a stick that has bindings
        sources.device_service.set_make_diagram(STICK, False)
        info = device_status(STICK, [FakeWrapper(stick_profile(), None)], sources)
        assert info.state is DeviceStatus.NO_DIAGRAM
        assert info.reason == "user" and info.reason_text == "Set by you"
        assert info.kind_source == "user"
        # A stale automatic value is not trusted: the live facts win
        sources.device_service.set_user_kind(STICK, None)
        sources.device_service.set_auto_kind(STICK, "other", "nothing_bound")
        assert device_status(
            STICK, [FakeWrapper(stick_profile(), None)], sources
        ).state is (DeviceStatus.NEEDS_TEMPLATE)

    def test_template_chain_ready_gaps_and_missing(self, sources, tmp_path):
        wrappers = [FakeWrapper(stick_profile("F-16C", 1), None)]
        assert (
            device_status(STICK, wrappers, sources).state is DeviceStatus.NEEDS_TEMPLATE
        )

        copy = tmp_path / "Gladiator.svg"
        shutil.copy(TEST_TEMPLATE, copy)
        sources.device_service.set_template(STICK, copy)
        ready = device_status(STICK, wrappers, sources)
        assert ready.state is DeviceStatus.READY
        assert ready.template_name == "Gladiator.svg"
        assert ready.template_key == f"user:{copy.resolve().as_posix()}"
        assert ready.missing_controls == [] and ready.profile_count == 1

        gaps = [FakeWrapper(stick_profile("Mirage", 1, 3), None)]
        info = device_status(STICK, wrappers + gaps, sources)
        assert info.state is DeviceStatus.READY_WITH_GAPS
        assert info.missing_controls == ["button_3"] and info.profile_count == 2

        copy.unlink()
        missing = device_status(STICK, wrappers, sources)
        assert missing.state is DeviceStatus.TEMPLATE_MISSING
        assert missing.template_name == "Gladiator.svg"
        assert missing.reason_text == "Template Gladiator.svg can't be found"
        # Nothing was deleted: the choice is still stored
        assert sources.device_service.template(STICK).path == str(copy)

    def test_moved_template_is_relinked_and_layouts_follow(self, sources, tmp_path):
        from joystick_diagrams.render.layout import HideOp

        wrappers = [FakeWrapper(stick_profile(), None)]
        my_templates = tmp_path / "My templates"
        my_templates.mkdir()
        old = tmp_path / "old" / "Gladiator.svg"
        old.parent.mkdir()
        shutil.copy(TEST_TEMPLATE, old)
        sources.device_service.set_template(STICK, old)
        old_key = sources.device_service.template(STICK).key
        sources.layout_service.append_op(
            old_key, "", HideOp(target="button_2"), "h", device_guid=STICK
        )

        moved = my_templates / "Gladiator.svg"
        shutil.move(old, moved)
        info = device_status(STICK, wrappers, sources)
        assert info.state is DeviceStatus.READY
        assert info.template_path == str(moved)
        new_key = f"user:{moved.resolve().as_posix()}"
        assert sources.device_service.template(STICK).key == new_key
        assert sources.layout_service.has_ops(new_key, None, STICK)
        assert not sources.layout_service.has_ops(old_key, None, STICK)

    def test_all_statuses_cover_the_read_and_the_remembered(self, sources):
        first = [FakeWrapper(stick_profile(), None)]
        sources.inventory.record_read(first)
        profile = Profile_("Ship")
        profile.add_device(VJOY, "vJoy Device")
        later = [FakeWrapper(profile, None, "Star Citizen")]
        statuses = all_device_statuses(later, sources)
        assert statuses[STICK].state is DeviceStatus.NOT_SEEN
        assert statuses[VJOY].state is DeviceStatus.NO_DIAGRAM
        assert set(all_device_statuses(later, sources, include_unseen=False)) == {VJOY}


def test_reason_text_words():
    assert reason_text(None) is None
    assert reason_text("nothing_bound_moved") == (
        "Nothing bound: its bindings are on your stick"
    )
    assert reason_text("legacy_hidden") == "Set by you"
    assert reason_text("merged_into") == "Listed twice: its bindings go on one diagram"
    assert reason_text("template_missing") == "Template can't be found"
    assert reason_text("something_else") == "Something else"
    assert reason_text("merged_into", merged_name="Stick") == "Same controller as Stick"
    assert DeviceStatus.READY_WITH_GAPS.exports and not DeviceStatus.NO_DIAGRAM.exports
