"""Tests for AppState._apply_input_routes — the routing pipeline step.

These exercise the static entrypoint without standing up AppState's DB-backed
singleton; they feed ProfileWrapper-like objects directly.
"""

from unittest.mock import MagicMock, patch

import pytest

from joystick_diagrams.conflict_strategy import AliasConflictStrategy
from joystick_diagrams.db.device_alias_service import DeviceAliasService
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input_routing import RouteKey, RouteTarget

VJOY_GUID = "492ead50-d1e0-11ef-8002-444553540000"
PHYS_GUID = "03f2f260-b49d-11ea-8001-444553540000"
MASTER_GUID = "aaaa0000-0000-0000-0000-000000000001"


def _wrapper_with_profile(profile: Profile_):
    """Minimal ProfileWrapper stand-in with a mutable `profile` attribute."""
    mock = MagicMock()
    mock.profile = profile
    return mock


class TestApplyInputRoutesPipeline:
    def test_command_moves_from_vjoy_profile_to_physical(self):
        """Classic DCS-on-vJoy + Gremlin-route-to-physical scenario."""
        from joystick_diagrams.app_state import AppState

        # DCS-style profile: command bound on vJoy, no physical device yet.
        dcs = Profile_("mode1")
        vjoy_dcs = dcs.add_device(VJOY_GUID, "vJoy Device")
        vjoy_dcs.create_input(Button(108), "Fire Weapon")

        # Gremlin-style profile: declares the route, physical device present,
        # empty vJoy device is also typical (remaps land there but carry no
        # commands).
        gremlin = Profile_("base")
        gremlin.add_device(PHYS_GUID, "Physical Stick")
        gremlin.input_routes[RouteKey(VJOY_GUID, "buttons", "BUTTON_108")] = [
            RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")
        ]

        wrappers = [_wrapper_with_profile(dcs), _wrapper_with_profile(gremlin)]

        AppState._apply_input_routes(
            wrappers, strategy=AliasConflictStrategy.CONCATENATE
        )

        # Command landed on physical device in DCS profile
        phys = dcs.get_device(PHYS_GUID)
        assert phys is not None, "physical device should be created in DCS profile"
        assert phys.get_input("buttons", "BUTTON_1").command == "Fire Weapon"
        # vJoy device has been drained and dropped
        assert VJOY_GUID not in dcs.devices

    def test_routes_from_multiple_wrappers_are_unioned(self):
        """A route declared in wrapper A should be applied to profile in wrapper B."""
        from joystick_diagrams.app_state import AppState

        dcs = Profile_("mode1")
        vjoy_dcs = dcs.add_device(VJOY_GUID, "vJoy Device")
        vjoy_dcs.create_input(Button(50), "Land Gear")

        gremlin = Profile_("base")
        gremlin.add_device(PHYS_GUID, "Physical Stick")
        gremlin.input_routes[RouteKey(VJOY_GUID, "buttons", "BUTTON_50")] = [
            RouteTarget(PHYS_GUID, "buttons", "BUTTON_2", "")
        ]

        wrappers = [_wrapper_with_profile(dcs), _wrapper_with_profile(gremlin)]

        AppState._apply_input_routes(
            wrappers, strategy=AliasConflictStrategy.CONCATENATE
        )

        assert (
            dcs.get_device(PHYS_GUID).get_input("buttons", "BUTTON_2").command
            == "Land Gear"
        )

    def test_no_routes_means_pipeline_is_noop(self):
        """Regression: profiles with no routes pass through unchanged."""
        from joystick_diagrams.app_state import AppState

        profile = Profile_("test")
        dev = profile.add_device(PHYS_GUID, "Physical Stick")
        dev.create_input(Button(1), "Fire")

        wrappers = [_wrapper_with_profile(profile)]

        AppState._apply_input_routes(
            wrappers, strategy=AliasConflictStrategy.CONCATENATE
        )

        assert PHYS_GUID in profile.devices
        assert (
            profile.get_device(PHYS_GUID).get_input("buttons", "BUTTON_1").command
            == "Fire"
        )

    def test_destination_device_name_resolved_from_another_profile(self):
        """If the DCS profile doesn't know the destination device name, the
        name should be looked up from the Gremlin profile that does."""
        from joystick_diagrams.app_state import AppState

        dcs = Profile_("mode1")
        vjoy_dcs = dcs.add_device(VJOY_GUID, "vJoy Device")
        vjoy_dcs.create_input(Button(108), "Fire Weapon")
        # Note: no PHYS device on DCS.

        gremlin = Profile_("base")
        gremlin.add_device(PHYS_GUID, "My Real Stick")
        gremlin.input_routes[RouteKey(VJOY_GUID, "buttons", "BUTTON_108")] = [
            RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")
        ]

        wrappers = [_wrapper_with_profile(dcs), _wrapper_with_profile(gremlin)]

        AppState._apply_input_routes(
            wrappers, strategy=AliasConflictStrategy.CONCATENATE
        )

        phys = dcs.get_device(PHYS_GUID)
        assert phys is not None
        assert phys.name == "My Real Stick"


@pytest.fixture
def mock_db_settings(monkeypatch):
    """Neutralise db-backed setting lookups for routing strategy."""
    from joystick_diagrams.db import db_settings

    monkeypatch.setattr(db_settings, "get_setting", lambda _key: None)


class TestProcessProfilesFromCollectionsOrder:
    """End-to-end: inheritance -> routing -> aliases ordering."""

    def test_routing_happens_before_alias_resolution(self, mock_db_settings):
        """With a user alias vJoy -> physical and a route vJoy.108 -> phys.1,
        the routing step should move command to phys.1 before aliasing runs
        (so the alias stage has nothing left on vJoy to merge)."""
        from joystick_diagrams.app_state import AppState

        dcs = Profile_("mode1")
        vjoy_dcs = dcs.add_device(VJOY_GUID, "vJoy Device")
        vjoy_dcs.create_input(Button(108), "Fire Weapon")

        gremlin = Profile_("base")
        gremlin.add_device(PHYS_GUID, "Physical Stick")
        gremlin.input_routes[RouteKey(VJOY_GUID, "buttons", "BUTTON_108")] = [
            RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")
        ]

        wrappers = [_wrapper_with_profile(dcs), _wrapper_with_profile(gremlin)]

        AppState._apply_input_routes(
            wrappers, strategy=AliasConflictStrategy.CONCATENATE
        )

        # After routing: command is on the physical device key 1 (not vJoy 108)
        phys = dcs.get_device(PHYS_GUID)
        assert phys.get_input("buttons", "BUTTON_1").command == "Fire Weapon"
        assert VJOY_GUID not in dcs.devices


@pytest.fixture()
def alias_service_phys_to_master():
    """DeviceAliasService aliasing PHYS_GUID -> MASTER_GUID."""
    with patch(
        "joystick_diagrams.db.device_alias_service.db_device_aliases"
    ) as mock_db:
        mock_db.get_all_aliases.return_value = [(PHYS_GUID, MASTER_GUID)]
        yield DeviceAliasService()


@pytest.fixture()
def alias_service_vjoy_to_phys():
    """DeviceAliasService aliasing VJOY_GUID -> PHYS_GUID (the naive mistake
    the routing feature fixes). Used to verify routing + alias composition."""
    with patch(
        "joystick_diagrams.db.device_alias_service.db_device_aliases"
    ) as mock_db:
        mock_db.get_all_aliases.return_value = [(VJOY_GUID, PHYS_GUID)]
        yield DeviceAliasService()


class TestRoutingXAlias:
    """Routing runs before alias resolution. Verify the compositions."""

    def test_routed_command_follows_subsequent_alias_to_third_device(
        self, mock_db_settings, alias_service_phys_to_master
    ):
        """Route: vJoy.108 -> PHYS.1; User alias: PHYS -> MASTER.
        End state: command ends up on MASTER.1."""
        from joystick_diagrams.app_state import AppState

        dcs = Profile_("mode1")
        vjoy_dcs = dcs.add_device(VJOY_GUID, "vJoy Device")
        vjoy_dcs.create_input(Button(108), "Fire Weapon")

        gremlin = Profile_("base")
        gremlin.add_device(PHYS_GUID, "Physical Stick")
        gremlin.input_routes[RouteKey(VJOY_GUID, "buttons", "BUTTON_108")] = [
            RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")
        ]

        wrappers = [_wrapper_with_profile(dcs), _wrapper_with_profile(gremlin)]

        AppState._apply_input_routes(
            wrappers, strategy=AliasConflictStrategy.CONCATENATE
        )
        # Now apply aliases (PHYS -> MASTER)
        dcs_after = AppState._apply_aliases_to_profile(
            dcs, alias_service_phys_to_master
        )

        master = dcs_after.get_device(MASTER_GUID)
        assert master is not None
        assert master.get_input("buttons", "BUTTON_1").command == "Fire Weapon"
        assert PHYS_GUID not in dcs_after.devices

    def test_routing_plus_vjoy_to_phys_alias_routed_and_unrouted_both_land(
        self, mock_db_settings, alias_service_vjoy_to_phys
    ):
        """User has the naive alias vJoy -> PHYS configured. One vJoy button
        has a Gremlin route (tempo target) and one does not. Both should
        ultimately end up on PHYS: routed via routing, unrouted via alias
        ID-match (existing behaviour)."""
        from joystick_diagrams.app_state import AppState

        dcs = Profile_("mode1")
        vjoy_dcs = dcs.add_device(VJOY_GUID, "vJoy Device")
        vjoy_dcs.create_input(Button(108), "Routed Cmd")
        vjoy_dcs.create_input(Button(5), "Unrouted Cmd")
        # DCS also has something on the physical device directly
        phys_dcs = dcs.add_device(PHYS_GUID, "Physical Stick")
        phys_dcs.create_input(Button(9), "Direct Phys Cmd")

        gremlin = Profile_("base")
        gremlin.add_device(PHYS_GUID, "Physical Stick")
        gremlin.input_routes[RouteKey(VJOY_GUID, "buttons", "BUTTON_108")] = [
            RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")
        ]

        wrappers = [_wrapper_with_profile(dcs), _wrapper_with_profile(gremlin)]

        # Pipeline in order: routing first, then alias.
        AppState._apply_input_routes(
            wrappers, strategy=AliasConflictStrategy.CONCATENATE
        )
        dcs_after = AppState._apply_aliases_to_profile(dcs, alias_service_vjoy_to_phys)

        phys = dcs_after.get_device(PHYS_GUID)
        assert phys is not None
        # Routed button: routing placed "Routed Cmd" on PHYS BUTTON_1
        assert phys.get_input("buttons", "BUTTON_1").command == "Routed Cmd"
        # Unrouted button: alias ID-matched onto PHYS BUTTON_5
        assert phys.get_input("buttons", "BUTTON_5").command == "Unrouted Cmd"
        # Pre-existing direct binding preserved
        assert phys.get_input("buttons", "BUTTON_9").command == "Direct Phys Cmd"
        # vJoy drained end-to-end
        assert VJOY_GUID not in dcs_after.devices
