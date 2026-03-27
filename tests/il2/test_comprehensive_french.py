#!/usr/bin/env python3
"""
Comprehensive test of French descriptions on different devices
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from joystick_diagrams.plugins.il2_sturmovik_plugin.il2_parser import IL2Parser


def test_comprehensive_french_descriptions():
    """Complete test of French descriptions on all devices"""
    # Use test directory
    test_dir = Path(__file__).parent.joinpath("data")

    # Initialize and process
    parser = IL2Parser(test_dir)
    profile_collection = parser.process_profiles()

    assert len(profile_collection.profiles) > 0, "Should have at least one profile"

    french_count = 0
    technical_count = 0
    total_inputs = 0

    for profile_name, profile in profile_collection.profiles.items():
        assert (
            len(profile.devices) > 0
        ), f"Profile '{profile_name}' should have at least one device"

        for device_guid, device in profile.devices.items():
            for input_type, inputs in device.inputs.items():
                for input_obj in inputs.values():
                    total_inputs += 1
                    command = input_obj.command
                    control = input_obj.input_control

                    # Verify control has identifier
                    assert hasattr(
                        control, "identifier"
                    ), f"Control should have identifier for command '{command}'"

                    # Check if command contains French description (has special characters or known French words)
                    is_french = any(
                        char in command for char in "àâäéèêëìîïòôöùûüç"
                    ) or any(
                        word in command.lower()
                        for word in [
                            "de",
                            "du",
                            "des",
                            "la",
                            "le",
                            "les",
                            "avec",
                            "toutes",
                            "armes",
                            "trim",
                            "profondeur",
                            "roulis",
                        ]
                    )

                    if is_french:
                        french_count += 1
                    else:
                        technical_count += 1

    # Verify we found inputs
    assert total_inputs > 0, "Should have parsed at least one input"

    # Verify French descriptions are present
    assert (
        french_count > 0
    ), "Should have at least some French descriptions in the test data"

    # Verify encoding is correct (no double-encoded UTF-8 artifacts)
    for profile_name, profile in profile_collection.profiles.items():
        for device_guid, device in profile.devices.items():
            for input_type, inputs in device.inputs.items():
                for input_obj in inputs.values():
                    command = input_obj.command
                    assert (
                        "â€™" not in command
                    ), f"Command should not contain double-encoded UTF-8: {command}"
                    assert (
                        "dâ€™" not in command
                    ), f"Command should not contain malformed apostrophes: {command}"


if __name__ == "__main__":
    test_comprehensive_french_descriptions()
