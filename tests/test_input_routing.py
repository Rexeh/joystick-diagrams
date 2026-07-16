"""Tests for cross-device input routing (apply_routes)."""

from joystick_diagrams.conflict_strategy import AliasConflictStrategy
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input_routing import (
    RouteKey,
    RouteTarget,
    apply_routes,
    union_profile_routes,
)

VJOY_GUID = "492ead50-d1e0-11ef-8002-444553540000"
PHYS_GUID = "03f2f260-b49d-11ea-8001-444553540000"
OTHER_GUID = "aaaa0000-0000-0000-0000-000000000001"


# --- Fixtures / helpers ---


def _profile_with_vjoy_button(button_id: int, command: str) -> Profile_:
    """Build a profile with a single button bound on the vJoy device."""
    profile = Profile_("test")
    vjoy = profile.add_device(VJOY_GUID, "vJoy Device")
    vjoy.create_input(Button(button_id), command)
    return profile


# --- apply_routes ---


class TestApplyRoutes:
    def test_route_moves_command_from_vjoy_to_physical(self):
        """Command bound on vJoy BUTTON_108 + route vJoy.108 -> PHYS.1 puts the
        command on PHYS BUTTON_1."""
        profile = _profile_with_vjoy_button(108, "Fire Weapon")
        profile.add_device(PHYS_GUID, "Physical Stick")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", ""),
            ]
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={PHYS_GUID: "Physical Stick"},
        )

        phys = profile.get_device(PHYS_GUID)
        assert phys.get_input("buttons", "BUTTON_1").command == "Fire Weapon"

    def test_routed_source_input_is_popped_and_empty_device_dropped(self):
        """After a route fires, the source input is removed from the vJoy
        device and the now-empty vJoy device is dropped from the profile."""
        profile = _profile_with_vjoy_button(108, "Fire Weapon")
        profile.add_device(PHYS_GUID, "Physical Stick")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", ""),
            ]
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={},
        )

        # vJoy device is dropped because its only input was routed away
        assert VJOY_GUID not in profile.devices

    def test_unrouted_vjoy_binding_stays(self):
        """A vJoy binding with no matching route stays put on the vJoy device."""
        profile = _profile_with_vjoy_button(77, "Unrouted")

        apply_routes(
            profile,
            union_routes={},
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={},
        )

        vjoy = profile.get_device(VJOY_GUID)
        assert vjoy is not None
        assert vjoy.get_input("buttons", "BUTTON_77").command == "Unrouted"

    def test_destination_device_is_created_if_missing(self):
        """If the destination physical device doesn't exist in the profile,
        apply_routes creates it (using the provided device_names lookup)."""
        profile = _profile_with_vjoy_button(108, "Fire Weapon")
        # No PHYS device in profile.

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", ""),
            ]
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={PHYS_GUID: "Physical Stick"},
        )

        phys = profile.get_device(PHYS_GUID)
        assert phys is not None
        assert phys.name == "Physical Stick"
        assert phys.get_input("buttons", "BUTTON_1").command == "Fire Weapon"

    def test_destination_device_created_with_unknown_name_if_not_found(self):
        """Fallback name when device isn't in the lookup."""
        profile = _profile_with_vjoy_button(108, "Fire Weapon")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", ""),
            ]
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={},
        )

        phys = profile.get_device(PHYS_GUID)
        assert phys is not None
        assert phys.name == "Unknown Device"

    def test_tempo_modifier_strategy_preserves_short_and_long(self):
        """Two routes landing on the same physical input under MODIFIER:
        primary = first command, second becomes a modifier keyed by its qualifier."""
        profile = Profile_("test")
        vjoy = profile.add_device(VJOY_GUID, "vJoy")
        vjoy.create_input(Button(108), "Fire Weapon")
        vjoy.create_input(Button(109), "Target Lock")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "Short"),
            ],
            RouteKey(VJOY_GUID, "buttons", "BUTTON_109"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "Long"),
            ],
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.MODIFIER,
            device_names={PHYS_GUID: "Physical Stick"},
        )

        phys = profile.get_device(PHYS_GUID)
        input_ = phys.get_input("buttons", "BUTTON_1")
        assert input_.command == "Fire Weapon"
        assert len(input_.modifiers) == 1
        assert input_.modifiers[0].modifiers == {"Long"}
        assert input_.modifiers[0].command == "Target Lock"

    def test_tempo_concatenate_strategy_joins_commands_with_qualifier(self):
        """Two tempo routes under CONCATENATE preserve the loser's qualifier
        as a bracketed prefix on the joined segment."""
        profile = Profile_("test")
        vjoy = profile.add_device(VJOY_GUID, "vJoy")
        vjoy.create_input(Button(108), "Fire Weapon")
        vjoy.create_input(Button(109), "Target Lock")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "Short"),
            ],
            RouteKey(VJOY_GUID, "buttons", "BUTTON_109"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "Long"),
            ],
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={PHYS_GUID: "Physical Stick"},
        )

        phys = profile.get_device(PHYS_GUID)
        assert (
            phys.get_input("buttons", "BUTTON_1").command
            == "Fire Weapon | [Long] Target Lock"
        )

    def test_existing_binding_plus_tempo_route_concatenate_shows_qualifier(self):
        """User's reported scenario: native DCS binding on physical button +
        routed tempo-long command under CONCATENATE. The qualifier must
        survive in the joined output so short/long context isn't lost."""
        profile = Profile_("test")
        vjoy = profile.add_device(VJOY_GUID, "vJoy")
        vjoy.create_input(Button(108), "Kneeboard ON/OFF")
        phys = profile.add_device(PHYS_GUID, "Physical Stick")
        phys.create_input(Button(3), "Kneeboard Next Page")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_3", "Long"),
            ],
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={},
        )

        assert (
            profile.get_device(PHYS_GUID).get_input("buttons", "BUTTON_3").command
            == "Kneeboard Next Page | [Long] Kneeboard ON/OFF"
        )

    def test_destination_with_existing_binding_merges_via_conflict_strategy(self):
        """Physical device already has its own binding on BUTTON_1 + a routed
        binding arrives: existing command wins primary; routed becomes loser."""
        profile = Profile_("test")
        vjoy = profile.add_device(VJOY_GUID, "vJoy")
        vjoy.create_input(Button(108), "Routed Cmd")
        phys = profile.add_device(PHYS_GUID, "Physical Stick")
        phys.create_input(Button(1), "Existing Cmd")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "Short"),
            ],
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.MODIFIER,
            device_names={},
        )

        input_ = profile.get_device(PHYS_GUID).get_input("buttons", "BUTTON_1")
        assert input_.command == "Existing Cmd"
        assert len(input_.modifiers) == 1
        assert input_.modifiers[0].modifiers == {"Short"}
        assert input_.modifiers[0].command == "Routed Cmd"

    def test_basic_route_concatenate_has_no_qualifier_prefix(self):
        """Route from a basic container has an empty qualifier; under
        CONCATENATE the joined string must be bare — no bracketed prefix,
        since the user didn't configure a tempo/toggle qualifier to label
        with. `[BUTTON_108]`-style prefixes would just add noise in the
        common basic-remap case."""
        profile = Profile_("test")
        vjoy = profile.add_device(VJOY_GUID, "vJoy")
        vjoy.create_input(Button(108), "Routed Cmd")
        phys = profile.add_device(PHYS_GUID, "Physical Stick")
        phys.create_input(Button(1), "Existing Cmd")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", ""),
            ],
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={},
        )

        assert (
            profile.get_device(PHYS_GUID).get_input("buttons", "BUTTON_1").command
            == "Existing Cmd | Routed Cmd"
        )

    def test_basic_route_modifier_uses_input_identifier_as_fallback(self):
        """Route from a basic container has an empty qualifier; under
        MODIFIER the promoted modifier's key-set falls back to the loser
        input's identifier (BUTTON_108) — more informative than a literal
        'routed' sentinel."""
        profile = Profile_("test")
        vjoy = profile.add_device(VJOY_GUID, "vJoy")
        vjoy.create_input(Button(108), "Routed Cmd")
        phys = profile.add_device(PHYS_GUID, "Physical Stick")
        phys.create_input(Button(1), "Existing Cmd")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", ""),
            ],
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.MODIFIER,
            device_names={},
        )

        input_ = profile.get_device(PHYS_GUID).get_input("buttons", "BUTTON_1")
        assert input_.command == "Existing Cmd"
        assert len(input_.modifiers) == 1
        assert input_.modifiers[0].modifiers == {"BUTTON_108"}
        assert input_.modifiers[0].command == "Routed Cmd"

    def test_non_empty_source_device_not_dropped(self):
        """Source device with other inputs keeps them after a partial route."""
        profile = Profile_("test")
        vjoy = profile.add_device(VJOY_GUID, "vJoy")
        vjoy.create_input(Button(108), "Routed Cmd")
        vjoy.create_input(Button(200), "Unrouted Cmd")

        routes = {
            RouteKey(VJOY_GUID, "buttons", "BUTTON_108"): [
                RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", ""),
            ],
        }

        apply_routes(
            profile,
            routes,
            strategy=AliasConflictStrategy.CONCATENATE,
            device_names={PHYS_GUID: "Physical Stick"},
        )

        vjoy = profile.get_device(VJOY_GUID)
        assert vjoy is not None
        assert vjoy.get_input("buttons", "BUTTON_108") is None
        assert vjoy.get_input("buttons", "BUTTON_200").command == "Unrouted Cmd"


class TestUnionProfileRoutes:
    def test_single_profile_routes_copied(self):
        profile = Profile_("test")
        key = RouteKey(VJOY_GUID, "buttons", "BUTTON_108")
        target = RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")
        profile.input_routes[key] = [target]

        result = union_profile_routes([profile])

        assert result == {key: [target]}

    def test_multiple_profiles_same_key_first_wins(self):
        """When two profiles declare the same route key with different targets,
        the first profile's target list wins (v1 behaviour)."""
        key = RouteKey(VJOY_GUID, "buttons", "BUTTON_108")
        p1 = Profile_("p1")
        p1.input_routes[key] = [RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")]
        p2 = Profile_("p2")
        p2.input_routes[key] = [RouteTarget(OTHER_GUID, "buttons", "BUTTON_5", "")]

        result = union_profile_routes([p1, p2])

        assert result[key] == [RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")]

    def test_disjoint_profiles_union(self):
        k1 = RouteKey(VJOY_GUID, "buttons", "BUTTON_108")
        k2 = RouteKey(VJOY_GUID, "buttons", "BUTTON_109")
        p1 = Profile_("p1")
        p1.input_routes[k1] = [RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")]
        p2 = Profile_("p2")
        p2.input_routes[k2] = [RouteTarget(PHYS_GUID, "buttons", "BUTTON_2", "")]

        result = union_profile_routes([p1, p2])

        assert result[k1] == [RouteTarget(PHYS_GUID, "buttons", "BUTTON_1", "")]
        assert result[k2] == [RouteTarget(PHYS_GUID, "buttons", "BUTTON_2", "")]
