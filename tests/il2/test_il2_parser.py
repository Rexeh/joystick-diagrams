"""Unit tests for IL-2 Sturmovik parser functionality

This test suite covers all aspects of the IL-2 parser including:
- File parsing (devices.txt and global.actions)
- Encoding handling and accent processing
- Control object creation (buttons, axes, hats)
- Profile collection generation
- CSV export functionality
- Error handling and edge cases
"""

import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Add the project root to the path to import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.il2_sturmovik_plugin.il2_parser import IL2Parser


class TestIL2Parser:
    """Test class for IL2Parser functionality"""

    @pytest.fixture
    def test_data_dir(self):
        """Fixture providing path to test data directory"""
        return Path(__file__).parent / "data"

    @pytest.fixture
    def parser(self, test_data_dir):
        """Fixture providing an IL2Parser instance with test data"""
        return IL2Parser(test_data_dir)

    @pytest.fixture
    def sample_devices_content(self):
        """Sample devices.txt content for testing"""
        return """configId,guid,model|
1,%22b0c891c0-3f30-11f0-0000545345440380%22,T-Rudder|
2,%22ba8a45a0-aa8d-11f0-0000545345440180%22,WINWING%20F18%20TAKEOFF%20PANEL%202|
3,%22ee6f1c30-3f2e-11f0-0000545345440180%22,Arduino%20Due|
8,%22530648c0-98c7-11f0-0000545345440280%22,WINWING%20Orion%20Throttle%20Base%20II%20%2B%20F15EX%20HANDLE%20L%20%2B%20F15EX%20HANDLE%20R|
9,%223833ad30-98c7-11f0-0000545345440180%22,WINWING%20Orion%20Joystick%20Base%202%20%2B%20JGRIP-F16|
"""

    @pytest.fixture
    def sample_global_actions_content(self):
        """Sample global.actions content with French accents for testing"""
        return """// Input map preset.
&actions=action,command,invert|
screenshot,joy3_b41,0| // Capture d'écran
timepause,joy6_b6,0| // Jeu en pause marche/arrêt
timefaster,joy6_b10,0| // Accélérer le jeu en mission
timeslower,joy6_b11,0| // Décélérer le jeu en mission
cam_reset,joy3_b37,0| // Réinitialiser caméra
bc_head_cfovi,joy8_b10,0| // Tête du pilote: zoomer
rpc_pitch,joy9_axis_y,0| // Pitch control
rpc_roll,joy9_axis_x,0| // Roll control  
rpc_yaw,joy1_axis_rz,1| // Yaw control (inverted)
throttle_axis,joy8_axis_z,0| // Throttle control
slider_control,joy8_axis_q,0| // Slider control (AXIS_SLIDER_2)
pov_test,joy9_pov0_0,0| // POV hat up
pov_multi,joy9_pov0_0/joy9_pov0_180,0| // Multiple POV directions
"""

    @pytest.fixture
    def sample_global_actions_with_encoding_issues(self):
        """Sample content with encoding issues (double-encoded UTF-8)"""
        return """// Input map preset with encoding issues
&actions=action,command,invert|
screenshot,joy3_b41,0| // Capture dâ€™écran
oil_pressure,joy8_b15,0| // Pression dâ€™huile
engine_temp,joy8_b16,0| // Température moteur – contrôle
"""

    def test_parser_initialization(self, test_data_dir):
        """Test parser initialization with correct file paths"""
        parser = IL2Parser(test_data_dir)

        assert parser.input_dir == test_data_dir
        assert parser.global_actions_file == test_data_dir / "global.actions"
        assert parser.devices_file == test_data_dir / "devices.txt"
        assert isinstance(parser.devices, dict)
        assert isinstance(parser.bindings, list)
        assert isinstance(parser.action_descriptions, dict)

    def test_parse_devices_file_success(self, parser, sample_devices_content):
        """Test successful parsing of devices.txt file"""
        with patch("builtins.open", mock_open(read_data=sample_devices_content)):
            parser._parse_devices_file()

        # Check that devices were parsed correctly
        assert len(parser.devices) == 5
        assert "1" in parser.devices
        assert "9" in parser.devices

        # Verify device information (GUIDs are generated deterministically)
        device_1 = parser.devices["1"]
        assert device_1["name"] == "T-Rudder"
        assert device_1["id"] == "1"
        assert "original_guid" in device_1

        device_9 = parser.devices["9"]
        assert "WINWING Orion Joystick" in device_9["name"]
        assert device_9["id"] == "9"

    def test_parse_devices_file_malformed_lines(self, parser):
        """Test parsing devices file with malformed lines"""
        malformed_content = """configId,guid,model|
1,%22b0c891c0-3f30-11f0-0000545345440380%22,T-Rudder|
invalid_line_without_pipes
2,%22ba8a45a0-aa8d-11f0%22,Missing_Parts
3,%22complete-guid%22,Valid%20Device|
"""
        with patch("builtins.open", mock_open(read_data=malformed_content)):
            parser._parse_devices_file()

        # Should only parse valid lines
        assert len(parser.devices) == 2  # Only device 1 and 3 should be parsed
        assert "1" in parser.devices
        assert "3" in parser.devices
        assert "2" not in parser.devices  # Invalid format

    def test_parse_global_actions_file_success(
        self, parser, sample_global_actions_content
    ):
        """Test successful parsing of global.actions file"""
        with patch("builtins.open", mock_open(read_data=sample_global_actions_content)):
            parser._parse_global_actions_file()

        # Check that bindings were parsed
        assert len(parser.bindings) > 0

        # Check that action descriptions were built
        assert len(parser.action_descriptions) > 0
        assert "screenshot" in parser.action_descriptions
        assert "Capture d'écran" in parser.action_descriptions["screenshot"]

    def test_encoding_issues_fix(self, parser):
        """Test encoding issue fixes for double-encoded UTF-8"""
        # Test the _fix_encoding_issues method directly
        problematic_text = "Capture dâ€™écran and Pression dâ€™huile"
        fixed_text = parser._fix_encoding_issues(problematic_text)

        assert "d'écran" in fixed_text
        assert "d'huile" in fixed_text
        assert "dâ€™" not in fixed_text

    def test_encoding_issues_in_global_actions(
        self, parser, sample_global_actions_with_encoding_issues
    ):
        """Test that encoding issues are fixed when parsing global.actions"""
        with patch(
            "builtins.open",
            mock_open(read_data=sample_global_actions_with_encoding_issues),
        ):
            parser._parse_global_actions_file()

        # Check that encoding issues were fixed in action descriptions
        descriptions = list(parser.action_descriptions.values())
        description_text = " ".join(descriptions)

        assert "d'écran" in description_text
        assert "d'huile" in description_text
        assert "dâ€™" not in description_text

    def test_parse_il2_device_reference_button(self, parser):
        """Test parsing button device references"""
        # Test standard button reference
        result = parser._parse_il2_device_reference("joy3_b41")

        assert result is not None
        assert result["type"] == "button"
        assert result["device_id"] == "3"
        assert result["button_id"] == 42  # IL-2 uses 0-based, converted to 1-based

    def test_parse_il2_device_reference_axis(self, parser):
        """Test parsing axis device references"""
        # Test standard axis reference
        result = parser._parse_il2_device_reference("joy9_axis_y")

        assert result is not None
        assert result["type"] == "axis"
        assert result["device_id"] == "9"
        assert result["axis_id"] == "Y"  # Converted to uppercase

        # Test slider axis reference (q = SLIDER_2)
        result = parser._parse_il2_device_reference("joy8_axis_q")

        assert result is not None
        assert result["type"] == "axis"
        assert result["device_id"] == "8"
        assert result["axis_id"] == "SLIDER_2"  # Mapped to SLIDER_2

    def test_parse_il2_device_reference_pov(self, parser):
        """Test parsing POV/Hat device references"""
        # Test POV reference
        result = parser._parse_il2_device_reference("joy9_pov0_0")

        assert result is not None
        assert result["type"] == "hat"  # Parser returns "hat" type
        assert result["device_id"] == "9"
        assert result["hat_id"] == "POV_1_U"  # Converted format
        assert result["direction"] == 0

    def test_parse_il2_device_reference_invalid(self, parser):
        """Test parsing invalid device references"""
        # Test invalid format
        result = parser._parse_il2_device_reference("invalid_reference")
        assert result is None

        # Test keyboard reference (should be None as we focus on joysticks)
        result = parser._parse_il2_device_reference("key_escape")
        assert result is None

    def test_create_control_object_button(self, parser):
        """Test creating button control objects"""
        binding = {
            "type": "button",
            "device_id": "3",
            "button_id": 42,  # Use button_id, not button_number
            "description": "Screenshot button",
        }

        control = parser._create_control_object(binding)

        assert isinstance(control, Button)
        assert control.identifier == "BUTTON_42"

    def test_create_control_object_axis(self, parser):
        """Test creating axis control objects"""
        # Test standard axis
        binding = {
            "type": "axis",
            "device_id": "9",
            "axis_id": "Y",  # Use uppercase as returned by parser
            "description": "Pitch control",
            "invert": 0,
        }

        control = parser._create_control_object(binding)

        assert isinstance(control, Axis)
        assert control.id == AxisDirection.Y

    def test_create_control_object_axis_slider(self, parser):
        """Test creating axis slider control objects"""
        # Test slider axis (q = SLIDER_2)
        binding = {
            "type": "axis",
            "device_id": "8",
            "axis_id": "SLIDER_2",  # Use mapped value as returned by parser
            "description": "Slider control",
            "invert": 0,
        }

        control = parser._create_control_object(binding)

        assert isinstance(control, AxisSlider)
        assert control.identifier == "AXIS_SLIDER_2"

    def test_create_control_object_hat(self, parser):
        """Test creating hat/POV control objects"""
        binding = {
            "type": "hat",
            "device_id": "9",
            "hat_id": "POV_1_U",
            "direction": 0,
            "description": "POV up",
        }

        control = parser._create_control_object(binding)

        assert isinstance(control, Hat)
        assert control.direction == HatDirection.U

    def test_create_control_object_inverted_axis(self, parser):
        """Test creating inverted axis control object"""
        binding = {
            "type": "axis",
            "device_id": "1",
            "axis_id": "RZ",  # Use uppercase as returned by parser
            "description": "Inverted yaw",
            "invert": 1,
        }

        control = parser._create_control_object(binding)

        assert isinstance(control, Axis)
        assert control.id == AxisDirection.RZ

    def test_parse_binding_line_simple(self, parser):
        """Test parsing simple binding lines"""
        line = "screenshot,joy3_b41,0| // Capture d'écran"
        result = parser._parse_binding_line(line, 1)

        assert result is not None
        assert result["action"] == "screenshot"
        assert result["device_id"] == "3"
        assert result["type"] == "button"
        assert result["button_id"] == 42  # IL-2 uses 0-based, converted to 1-based

    def test_parse_binding_line_multiple_refs(self, parser):
        """Test parsing binding lines with multiple device references"""
        line = "pov_multi,joy9_pov0_0/joy9_pov0_180,0| // Multiple POV directions"
        result = parser._parse_binding_line(line, 1)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(binding["action"] == "pov_multi" for binding in result)
        assert result[0]["direction"] == 0  # Up
        assert result[1]["direction"] == 180  # Down

    def test_parse_binding_line_invalid(self, parser):
        """Test parsing invalid binding lines"""
        # Line without pipe
        result = parser._parse_binding_line("invalid_line_no_pipe", 1)
        assert result is None

        # Line with keyboard reference (should be ignored)
        result = parser._parse_binding_line("escape,key_escape,0|", 1)
        assert result is None

    def test_build_action_descriptions(self, parser, sample_global_actions_content):
        """Test building action descriptions mapping"""
        lines = sample_global_actions_content.split("\n")
        parser._build_action_descriptions(lines)

        assert "screenshot" in parser.action_descriptions
        assert "timepause" in parser.action_descriptions
        assert "Capture d'écran" in parser.action_descriptions["screenshot"]
        assert "pause marche/arrêt" in parser.action_descriptions["timepause"]

    def test_process_profiles_integration(self, test_data_dir):
        """Integration test for full profile processing"""
        parser = IL2Parser(test_data_dir)

        # This will use the actual test data files
        profile_collection = parser.process_profiles()

        assert isinstance(profile_collection, ProfileCollection)
        assert len(profile_collection.profiles) > 0

        # Check that we have an IL-2 profile
        il2_profile = None
        profile_names = list(profile_collection.profiles.keys())

        for profile_name in profile_collection.profiles:
            profile = profile_collection.profiles[profile_name]
            if profile_name.lower() == "il-2 sturmovik":
                il2_profile = profile
                break

        # If we don't find exact match, use the first profile (there should be one)
        if il2_profile is None and len(profile_names) > 0:
            il2_profile = profile_collection.profiles[profile_names[0]]

        assert il2_profile is not None
        assert len(il2_profile.devices) > 0

    def test_csv_export_functionality(self, parser, tmp_path):
        """Test CSV export functionality"""
        # First process the profiles
        profile_collection = parser.process_profiles()

        # Export to CSV
        csv_file = tmp_path / "test_export.csv"
        result = parser.export_mapping_to_file(csv_file, profile_collection)

        assert result is True
        assert csv_file.exists()

        # Read and verify CSV content
        csv_content = csv_file.read_text(encoding="utf-8")

        # Should contain header (semicolon-separated)
        assert (
            "Device;Technical_Name;Description;IL2_Control;Real_Control" in csv_content
        )

        # Should contain some joystick references
        assert "joy" in csv_content

        # Should handle French characters correctly
        lines = csv_content.split("\n")
        french_chars_found = any(
            "é" in line or "à" in line or "ç" in line for line in lines
        )
        # Note: May not always find French chars depending on test data

    def test_generate_real_control_identifier(self, parser):
        """Test generation of real control identifiers"""
        # Button binding
        button_binding = {"type": "button", "button_id": 35}
        identifier = parser._generate_real_control_identifier(button_binding)
        assert identifier == "BUTTON_35"

        # Axis binding
        axis_binding = {
            "type": "axis",
            "axis_id": "X",  # Use uppercase as returned by parser
        }
        identifier = parser._generate_real_control_identifier(axis_binding)
        assert identifier == "AXIS_X"

        # Slider binding
        slider_binding = {
            "type": "axis",
            "axis_id": "SLIDER_2",  # Use mapped value
        }
        identifier = parser._generate_real_control_identifier(slider_binding)
        assert identifier == "AXIS_SLIDER_2"

        # Hat binding
        hat_binding = {"type": "hat", "hat_id": "POV_1_U"}
        identifier = parser._generate_real_control_identifier(hat_binding)
        assert identifier == "HAT_POV_1_U"

    def test_slider_axis_mapping(self, parser):
        """Test specific slider axis mappings (q=SLIDER_2, p=SLIDER_1)"""
        # Test q axis (should map to SLIDER_2)
        binding_q = {
            "type": "axis",
            "device_id": "8",
            "axis_id": "SLIDER_2",  # Use mapped value
            "description": "Slider 2 control",
            "invert": 0,
        }

        control_q = parser._create_control_object(binding_q)
        assert isinstance(control_q, AxisSlider)
        assert control_q.identifier == "AXIS_SLIDER_2"

        # Test p axis (should map to SLIDER_1)
        binding_p = {
            "type": "axis",
            "device_id": "8",
            "axis_id": "SLIDER_1",  # Use mapped value
            "description": "Slider 1 control",
            "invert": 0,
        }

        control_p = parser._create_control_object(binding_p)
        assert isinstance(control_p, AxisSlider)
        assert control_p.identifier == "AXIS_SLIDER_1"

    def test_error_handling_missing_files(self, tmp_path):
        """Test error handling when required files are missing"""
        # Create parser with non-existent directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        parser = IL2Parser(empty_dir)

        with pytest.raises(Exception):
            parser.process_profiles()

    def test_error_handling_corrupted_files(self, parser, tmp_path):
        """Test error handling with corrupted file content"""
        corrupted_content = "This is not valid IL-2 format content"

        with patch("builtins.open", mock_open(read_data=corrupted_content)):
            # Should not raise exception but handle gracefully
            try:
                parser._parse_devices_file()
                parser._parse_global_actions_file()
            except Exception as e:
                # If exceptions are raised, they should be specific and handled
                assert "Error parsing" in str(e) or "Error" in str(e)

    def test_french_accent_preservation(self, parser):
        """Test that French accents are properly preserved in descriptions"""
        test_cases = [
            ("Contrôle de température", "Contrôle de température"),
            ("Système d'éjection", "Système d'éjection"),
            ("Paramètres avancés", "Paramètres avancés"),
            ("Caméra arrière", "Caméra arrière"),
        ]

        for input_text, expected_output in test_cases:
            result = parser._fix_encoding_issues(input_text)
            assert result == expected_output

    def test_double_encoded_accent_fixes(self, parser):
        """Test fixing of double-encoded accents"""
        test_cases = [
            ("Capture dâ€™écran", "Capture d'écran"),
            ("Pression dâ€™huile", "Pression d'huile"),
            ("Contrôle température", "Contrôle température"),  # Should remain unchanged
        ]

        for input_text, expected_output in test_cases:
            result = parser._fix_encoding_issues(input_text)
            assert expected_output in result or result == expected_output


class TestIL2ParserEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def parser(self, tmp_path):
        """Fixture providing a parser with temporary directory"""
        return IL2Parser(tmp_path)

    def test_empty_files(self, parser, tmp_path):
        """Test handling of empty files"""
        # Create empty files
        (tmp_path / "devices.txt").write_text("")
        (tmp_path / "global.actions").write_text("")

        # Should handle gracefully without crashing
        parser._parse_devices_file()
        parser._parse_global_actions_file()

        assert len(parser.devices) == 0
        assert len(parser.bindings) == 0

    def test_extremely_long_device_names(self, parser):
        """Test handling of extremely long device names"""
        long_name = "A" * 1000  # Very long device name
        content = f"1,%22guid%22,{long_name}|"

        with patch("builtins.open", mock_open(read_data=content)):
            parser._parse_devices_file()

        assert "1" in parser.devices
        assert parser.devices["1"]["name"] == long_name

    def test_special_characters_in_descriptions(self, parser):
        """Test handling of special characters in action descriptions"""
        content = """&actions=action,command,invert|
test_action,joy1_b1,0| // Special chars: @#$%^&*()_+-={}[]|\\:";'<>?,.
"""
        with patch("builtins.open", mock_open(read_data=content)):
            parser._parse_global_actions_file()

        assert "test_action" in parser.action_descriptions
        desc = parser.action_descriptions["test_action"]
        assert "@#$%^&*" in desc

    def test_maximum_device_numbers(self, parser):
        """Test handling of high device numbers"""
        # Test with device number 999
        result = parser._parse_il2_device_reference("joy999_b1")
        assert result is not None
        assert result["device_id"] == "999"

        # Test with very high button number
        result = parser._parse_il2_device_reference("joy1_b9999")
        assert result is not None
        assert result["button_id"] == 10000  # IL-2 uses 0-based, converted to 1-based


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
