"""Tests for Joystick Gremlin XML Parser."""

from pathlib import Path

import pytest

from joystick_diagrams.exceptions import JoystickDiagramsError
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
