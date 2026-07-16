"""Tests for Joystick Gremlin XML Parser."""

from pathlib import Path

import pytest

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.input_routing import RouteKey, RouteTarget
from joystick_diagrams.plugins.joystick_gremlin_plugin.joystick_gremlin import (
    JoystickGremlinParser,
)

TEST_DATA_DIR = Path("./tests/data/joystick_gremlin")

THROTTLE_GUID = "01de0a30-b49f-11ea-8002-444553540000"
STICK_GUID = "03f2f260-b49d-11ea-8001-444553540000"


# --- Fixtures ---


@pytest.fixture
def parser_inherit():
    return JoystickGremlinParser(TEST_DATA_DIR / "gremlin_inherit_no_inherit.xml")


@pytest.fixture
def parser_hat_buttons():
    return JoystickGremlinParser(
        TEST_DATA_DIR / "gremlin_pov_container_hat_buttons.xml"
    )


@pytest.fixture
def parser_virtual_buttons():
    return JoystickGremlinParser(TEST_DATA_DIR / "gremlin_hat_virtual_buttons.xml")


@pytest.fixture
def parser_vjoy_routing():
    return JoystickGremlinParser(TEST_DATA_DIR / "gremlin_vjoy_routing.xml")


PHYSICAL_STICK_GUID_VJOY = "03f2f260-b49d-11ea-8001-444553540000"
VJOY_DEVICE_1_GUID = "492ead50-d1e0-11ef-8002-444553540000"


# --- Validation Tests ---


class TestValidation:
    def test_no_devices_raises_error(self):
        with pytest.raises(JoystickDiagramsError):
            JoystickGremlinParser(TEST_DATA_DIR / "gremlin_no_devices.xml")

    def test_invalid_file_raises_error(self, tmp_path):
        bad_file = tmp_path / "bad.xml"
        bad_file.write_text('<?xml version="1.0" ?><root/>')
        with pytest.raises(JoystickDiagramsError):
            JoystickGremlinParser(bad_file)


# --- Button Parsing Tests ---


class TestButtonParsing:
    def test_button_with_description(self, parser_hat_buttons):
        collection = parser_hat_buttons.create_dictionary()
        profile = collection.get_profile("default")
        device = profile.get_device(STICK_GUID)

        button_1 = device.get_input("buttons", "BUTTON_1")
        assert button_1 is not None
        assert button_1.command == "DESC1"

        button_2 = device.get_input("buttons", "BUTTON_2")
        assert button_2 is not None
        assert button_2.command == "DESC2"

    def test_button_without_description_skipped(self, parser_inherit):
        collection = parser_inherit.create_dictionary()
        # Base mode on Stick device: buttons 1 and 2 have empty descriptions
        base_profile = collection.get_profile("base")
        stick_device = base_profile.get_device(STICK_GUID)

        assert stick_device.get_input("buttons", "BUTTON_1") is None
        assert stick_device.get_input("buttons", "BUTTON_2") is None


# --- Axis Parsing Tests ---


class TestAxisParsing:
    def test_axis_with_description(self, parser_inherit):
        """Axis 3 on Stick in A10 mode has description 'Speedbrake'."""
        collection = parser_inherit.create_dictionary()
        a10_profile = collection.get_profile("a10")
        stick = a10_profile.get_device(STICK_GUID)

        axis_z = stick.get_input("axis", "AXIS_Z")
        assert axis_z is not None
        assert axis_z.command == "Speedbrake"

    def test_axis_without_description_skipped(self, parser_inherit):
        """Axes with empty descriptions should not be created."""
        collection = parser_inherit.create_dictionary()
        a10_profile = collection.get_profile("a10")
        stick = a10_profile.get_device(STICK_GUID)

        # Axis 1 and 2 on Stick A10 mode have empty descriptions
        assert stick.get_input("axis", "AXIS_X") is None
        assert stick.get_input("axis", "AXIS_Y") is None


# --- Hat Button Container Tests (hat_buttons type) ---


class TestHatButtonContainer:
    def test_eight_way_hat_with_descriptions(self, parser_hat_buttons):
        collection = parser_hat_buttons.create_dictionary()
        profile = collection.get_profile("default")
        device = profile.get_device(STICK_GUID)

        # Hat 1 is 8-way, only directions 1 (U) and 5 (D) have descriptions
        hat_u = device.get_input("hats", "POV_1_U")
        assert hat_u is not None
        assert hat_u.command == "BUTTON U"

        hat_d = device.get_input("hats", "POV_1_D")
        assert hat_d is not None
        assert hat_d.command == "BUTTON D"

        # Directions without descriptions should not be present
        assert device.get_input("hats", "POV_1_UR") is None
        assert device.get_input("hats", "POV_1_R") is None
        assert device.get_input("hats", "POV_1_DR") is None
        assert device.get_input("hats", "POV_1_DL") is None
        assert device.get_input("hats", "POV_1_L") is None
        assert device.get_input("hats", "POV_1_UL") is None

    def test_four_way_hat_with_descriptions(self, parser_hat_buttons):
        collection = parser_hat_buttons.create_dictionary()
        profile = collection.get_profile("default")
        device = profile.get_device(STICK_GUID)

        # Hat 2 is 4-way: positions 1->U, 2->R, 3->D, 4->L
        hat_u = device.get_input("hats", "POV_2_U")
        assert hat_u is not None
        assert hat_u.command == "BUTTON U"

        hat_d = device.get_input("hats", "POV_2_D")
        assert hat_d is not None
        assert hat_d.command == "BUTTON D"

        hat_l = device.get_input("hats", "POV_2_L")
        assert hat_l is not None
        assert hat_l.command == "BUTTON L"

        # Position 2 (R direction) has no description
        assert device.get_input("hats", "POV_2_R") is None


# --- Virtual Button Container Tests (basic type with virtual-button) ---


class TestVirtualButtonContainer:
    def test_virtual_button_with_description(self, parser_virtual_buttons):
        collection = parser_virtual_buttons.create_dictionary()
        profile = collection.get_profile("default")
        device = profile.get_device(STICK_GUID)

        # Container 1 has description "Desc 1" and virtual-button with north, east, north-east
        # These map to U, R, UR directions
        hat_u = device.get_input("hats", "POV_1_U")
        assert hat_u is not None
        assert hat_u.command == "Desc 1"

        hat_r = device.get_input("hats", "POV_1_R")
        assert hat_r is not None
        assert hat_r.command == "Desc 1"

        hat_ur = device.get_input("hats", "POV_1_UR")
        assert hat_ur is not None
        assert hat_ur.command == "Desc 1"

    def test_virtual_button_without_description_skipped(self, parser_virtual_buttons):
        collection = parser_virtual_buttons.create_dictionary()
        profile = collection.get_profile("default")
        device = profile.get_device(STICK_GUID)

        # Container 2 has virtual-button south-east but no description element
        # Should be skipped
        assert device.get_input("hats", "POV_1_DR") is None


# --- Mode Inheritance Tests ---


class TestModeInheritance:
    def test_base_mode_unaffected_by_inheritance(self, parser_inherit):
        """Base mode should retain only its own bindings after inheritance resolution."""
        collection = parser_inherit.create_dictionary()
        base_profile = collection.get_profile("base")
        throttle = base_profile.get_device(THROTTLE_GUID)

        assert throttle.get_input("buttons", "BUTTON_1").command == "Base No Replace"
        assert throttle.get_input("buttons", "BUTTON_2").command == "Base Replacement"
        assert throttle.get_input("buttons", "BUTTON_56").command == "A10 Mode"
        assert throttle.get_input("buttons", "BUTTON_57").command == "F18 Mode"
        assert throttle.get_input("buttons", "BUTTON_58").command == "KA50 Mode"

        # Base should NOT have A10-specific buttons
        assert throttle.get_input("buttons", "BUTTON_5") is None
        assert throttle.get_input("buttons", "BUTTON_6") is None
        assert throttle.get_input("buttons", "BUTTON_7") is None

    def test_standalone_mode_no_inherit(self, parser_inherit):
        """KA50 mode on throttle has no inherit - only its own bindings."""
        collection = parser_inherit.create_dictionary()
        ka50_profile = collection.get_profile("ka50")
        throttle = ka50_profile.get_device(THROTTLE_GUID)

        assert throttle.get_input("buttons", "BUTTON_1").command == "KA50 Button 1"
        assert throttle.get_input("buttons", "BUTTON_2").command == "KA50 Button 2"
        assert throttle.get_input("buttons", "BUTTON_55").command == "KA50 Button 55"

        # Should NOT have Base bindings
        assert throttle.get_input("buttons", "BUTTON_56") is None
        assert throttle.get_input("buttons", "BUTTON_57") is None
        assert throttle.get_input("buttons", "BUTTON_58") is None

    def test_empty_mode_inherits_all_from_parent(self, parser_inherit):
        """FA18 mode on throttle is empty and inherits from Base - gets all Base bindings."""
        collection = parser_inherit.create_dictionary()
        fa18_profile = collection.get_profile("fa18")
        throttle = fa18_profile.get_device(THROTTLE_GUID)

        assert throttle.get_input("buttons", "BUTTON_1").command == "Base No Replace"
        assert throttle.get_input("buttons", "BUTTON_2").command == "Base Replacement"
        assert throttle.get_input("buttons", "BUTTON_56").command == "A10 Mode"
        assert throttle.get_input("buttons", "BUTTON_57").command == "F18 Mode"
        assert throttle.get_input("buttons", "BUTTON_58").command == "KA50 Mode"

    def test_child_overrides_parent(self, parser_inherit):
        """A10 mode inherits Base: child descriptions override parent, empty inherits parent."""
        collection = parser_inherit.create_dictionary()
        a10_profile = collection.get_profile("a10")
        throttle = a10_profile.get_device(THROTTLE_GUID)

        # Button 1: A10 has its own description, overrides Base
        assert (
            throttle.get_input("buttons", "BUTTON_1").command == "Button 1 - No Replace"
        )

        # Button 2: A10 has empty description (skipped), so inherits Base's "Base Replacement"
        assert throttle.get_input("buttons", "BUTTON_2").command == "Base Replacement"

        # A10-specific buttons
        assert throttle.get_input("buttons", "BUTTON_5").command == "Pinkie Center"
        assert throttle.get_input("buttons", "BUTTON_6").command == "Pinkie Forward"
        assert throttle.get_input("buttons", "BUTTON_7").command == "Pinkie Aft"

        # Inherited from Base
        assert throttle.get_input("buttons", "BUTTON_56").command == "A10 Mode"
        assert throttle.get_input("buttons", "BUTTON_57").command == "F18 Mode"
        assert throttle.get_input("buttons", "BUTTON_58").command == "KA50 Mode"

    def test_multi_device_inheritance_independent(self, parser_inherit):
        """Each device resolves inheritance independently within the same mode."""
        collection = parser_inherit.create_dictionary()

        # A10 on Stick: NOT inherited (no inherit attribute on Stick's A10 mode)
        a10_profile = collection.get_profile("a10")
        stick = a10_profile.get_device(STICK_GUID)
        assert stick.get_input("buttons", "BUTTON_1").command == "Trim Up"
        assert stick.get_input("buttons", "BUTTON_2").command == "Trim Right"

        # A10 on Throttle: inherited from Base
        throttle = a10_profile.get_device(THROTTLE_GUID)
        assert throttle.get_input("buttons", "BUTTON_56").command == "A10 Mode"

    def test_inherited_mode_with_own_bindings_on_stick(self, parser_inherit):
        """KA50 on Stick inherits from Base, has Gun Fire button."""
        collection = parser_inherit.create_dictionary()
        ka50_profile = collection.get_profile("ka50")
        stick = ka50_profile.get_device(STICK_GUID)

        # KA50 on Stick inherits Base (empty) + own Gun Fire
        assert stick.get_input("buttons", "BUTTON_6").command == "Gun Fire"

    def test_profile_count(self, parser_inherit):
        """Should have 4 profiles: base, a10, fa18, ka50."""
        collection = parser_inherit.create_dictionary()
        assert len(collection) == 4
        assert collection.get_profile("base") is not None
        assert collection.get_profile("a10") is not None
        assert collection.get_profile("fa18") is not None
        assert collection.get_profile("ka50") is not None


# --- vJoy Routing Tests ---


class TestVjoyRouting:
    def test_basic_container_produces_single_route_with_empty_qualifier(
        self, parser_vjoy_routing
    ):
        """<container type="basic"> with one <remap button="7" vjoy="1"/> yields
        a single route keyed on vJoy BUTTON_7 with qualifier ""."""
        collection = parser_vjoy_routing.create_dictionary()
        profile = collection.get_profile("default")

        key = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_7")
        assert key in profile.input_routes

        targets = profile.input_routes[key]
        assert len(targets) == 1
        assert targets[0] == RouteTarget(
            PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_1", ""
        )

    def test_tempo_container_produces_short_and_long_routes(self, parser_vjoy_routing):
        """<container type="tempo"> with two action-sets yields two routes,
        qualifiers 'Short' then 'Long'."""
        collection = parser_vjoy_routing.create_dictionary()
        profile = collection.get_profile("default")

        short_key = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_108")
        long_key = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_109")

        assert profile.input_routes[short_key] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_2", "Short")
        ]
        assert profile.input_routes[long_key] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_2", "Long")
        ]

    def test_conditional_container_produces_conditional_qualifier(
        self, parser_vjoy_routing
    ):
        """A basic container with an <activation-condition> child yields a
        route qualifier 'Conditional'."""
        collection = parser_vjoy_routing.create_dictionary()
        profile = collection.get_profile("default")

        key = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_50")
        assert profile.input_routes[key] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_3", "Conditional")
        ]

    def test_axis_remap_produces_axis_route(self, parser_vjoy_routing):
        """<remap axis="4" vjoy="1"/> on a physical AXIS_X yields an axis-typed
        route keyed on vJoy AXIS_RX."""
        collection = parser_vjoy_routing.create_dictionary()
        profile = collection.get_profile("default")

        key = RouteKey(VJOY_DEVICE_1_GUID, "axis", "AXIS_RX")
        assert profile.input_routes[key] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "axis", "AXIS_X", "")
        ]

    def test_no_routes_on_profiles_without_remaps(self, parser_hat_buttons):
        """Existing fixtures without <remap> should have empty input_routes."""
        collection = parser_hat_buttons.create_dictionary()
        for profile in collection.profiles.values():
            assert profile.input_routes == {}


@pytest.fixture
def parser_route_inheritance():
    return JoystickGremlinParser(TEST_DATA_DIR / "gremlin_route_inheritance.xml")


class TestRouteInheritance:
    def test_child_inherits_parent_routes_when_missing(self, parser_route_inheritance):
        """Combat inherits Base; Combat has no route for BUTTON_50 (Base's route
        on physical BUTTON_1) so it should inherit it."""
        collection = parser_route_inheritance.create_dictionary()
        combat = collection.get_profile("combat")

        key_50 = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_50")
        assert combat.input_routes[key_50] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_1", "")
        ]

    def test_child_overrides_parent_route_for_same_source_key(
        self, parser_route_inheritance
    ):
        """Combat defines its own route for BUTTON_99 on physical BUTTON_2 and
        does NOT inherit Base's BUTTON_60->BUTTON_2 route for the same physical
        target. Specifically: Combat's input_routes has BUTTON_99 but not
        BUTTON_60 (Base's override)."""
        collection = parser_route_inheritance.create_dictionary()
        combat = collection.get_profile("combat")

        key_99 = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_99")
        assert combat.input_routes[key_99] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_2", "")
        ]

        # Base had BUTTON_60 -> BUTTON_2. Combat overrides physical BUTTON_2 with
        # its own <remap>, so the parent route for BUTTON_60 should not be
        # inherited (the physical input already has its own binding in Combat).
        key_60 = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_60")
        assert key_60 not in combat.input_routes

    def test_base_mode_unchanged_by_inheritance(self, parser_route_inheritance):
        """Base's own routes should remain intact."""
        collection = parser_route_inheritance.create_dictionary()
        base = collection.get_profile("base")

        key_50 = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_50")
        key_60 = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_60")
        assert key_50 in base.input_routes
        assert key_60 in base.input_routes


@pytest.fixture
def parser_container_qualifiers():
    return JoystickGremlinParser(TEST_DATA_DIR / "gremlin_container_qualifiers.xml")


class TestContainerQualifiers:
    def test_smart_toggle_produces_toggle_qualifier(self, parser_container_qualifiers):
        """<container type="smart_toggle"> with one action-set yields
        qualifier 'Toggle'."""
        collection = parser_container_qualifiers.create_dictionary()
        profile = collection.get_profile("default")

        key = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_10")
        assert profile.input_routes[key] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_1", "Toggle")
        ]

    def test_double_tap_produces_single_and_double_qualifiers(
        self, parser_container_qualifiers
    ):
        """<container type="double_tap"> with two action-sets yields
        qualifiers 'Single' then 'Double'."""
        collection = parser_container_qualifiers.create_dictionary()
        profile = collection.get_profile("default")

        single_key = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_20")
        double_key = RouteKey(VJOY_DEVICE_1_GUID, "buttons", "BUTTON_21")

        assert profile.input_routes[single_key] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_2", "Single")
        ]
        assert profile.input_routes[double_key] == [
            RouteTarget(PHYSICAL_STICK_GUID_VJOY, "buttons", "BUTTON_2", "Double")
        ]
