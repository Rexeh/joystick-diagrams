#!/usr/bin/env python3
"""Very simple test to diagnose button creation problem"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from joystick_diagrams.plugins.il2_sturmovik_plugin.il2_parser import IL2Parser


def test_button_creation():
    """Simple button creation test"""
    test_dir = Path(__file__).parent.joinpath("data")
    parser = IL2Parser(test_dir)

    # Direct parsing test
    result = parser._parse_il2_device_reference("joy3_b34")
    assert result is not None, "Should successfully parse joy3_b34 reference"
    assert result.get("type") == "button", "Reference should be parsed as button type"

    # Control object creation test
    control = parser._create_control_object(result)
    assert control is not None, "Control object should be created successfully"
    assert hasattr(control, "identifier"), "Control should have identifier attribute"
    assert hasattr(control, "id"), "Control should have button_id attribute"

    # Complete binding test for escape (joy3_b34)
    profile_collection = parser.process_profiles()
    assert profile_collection is not None, "Profile collection should be created"

    # Find joy3_b34 binding
    joy3_bindings = [b for b in parser.bindings if b["device_ref"] == "joy3_b34"]
    assert len(joy3_bindings) > 0, "Should find at least one binding for joy3_b34"

    for binding in joy3_bindings:
        # Test control creation
        control = parser._create_control_object(binding)
        assert control is not None, f"Control should be created for binding: {binding}"


if __name__ == "__main__":
    test_button_creation()
