from dataclasses import dataclass
from datetime import datetime

import pytest

from joystick_diagrams.export.export import (
    TEMPLATE_DATING_KEY,
    TEMPLATE_NAMING_KEY,
    populate_template,
    replace_input_modifier_id_key,
    replace_input_modifiers_string,
    replace_input_string,
    replace_template_date_string,
    replace_template_name_string,
    replace_unused_keys,
    sanitize_string_for_svg,
)
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.modifier import Modifier
from joystick_diagrams.input.types.axis import Axis, AxisDirection
from joystick_diagrams.input.types.button import Button
from joystick_diagrams.input.types.hat import Hat, HatDirection

# Unit Tests


def test_replacement_of_name_string():
    test_string = '<testData>STRING="ABC">{}<testData>'
    test_data = test_string.format(TEMPLATE_NAMING_KEY)
    replacement = "Profile 123 - Name"

    rep = replace_template_name_string(replacement, test_data)

    assert rep == test_string.format(replacement)


def test_replacement_of_date_string():
    test_string = '<testData>STRING="ABC">{}<testData>'
    test_data = test_string.format(TEMPLATE_DATING_KEY)

    rep = replace_template_date_string(test_data)

    assert rep == test_string.format(datetime.now().strftime("%d/%m/%Y"))


def test_unused_keys_cleanup_buttons():
    test_string = '<testData>STRING="ABC">{}<testData>'
    controls = ["BUTTON_1", "BUTTON_4", "BUTTON_120"]
    test_data = test_string.format("|".join(controls))

    rep = replace_unused_keys(test_data)

    assert rep == test_string.format("|" * (len(controls) - 1))


def test_unused_keys_cleanup_axis():
    test_string = '<testData>STRING="ABC">{}<testData>'
    controls = ["AXIS_X", "AXIS_Y", "AXIS_RZ", "AXIS_SLIDER_1"]
    test_data = test_string.format("|".join(controls))

    rep = replace_unused_keys(test_data)

    assert rep == test_string.format("|" * (len(controls) - 1))


def test_unused_keys_cleanup_hats():
    test_string = '<testData>STRING="ABC">{}<testData>'
    controls = ["POV_1_U", "POV_1_UR", "POV_4_DR"]
    test_data = test_string.format("|".join(controls))

    rep = replace_unused_keys(test_data)

    assert rep == test_string.format("|" * (len(controls) - 1))


def test_unused_keys_cleanup_modifiers():
    test_string = '<testData>STRING="ABC">{}<testData>'
    controls = [
        # Buttons
        "BUTTON_1_MODIFIERS",
        "BUTTON_1_MODIFIER_1",
        "BUTTON_1_MODIFIER_1_KEY",
        "BUTTON_1_MODIFIER_1_COMMAND",
        # Normal AXIS
        "AXIS_X_MODIFIERS",
        "AXIS_X_MODIFIER_1",
        "AXIS_X_MODIFIER_1_KEY",
        "AXIS_X_MODIFIER_1_COMMAND",
        # Slider AXIS
        "AXIS_SLIDER_1_MODIFIERS",
        "AXIS_SLIDER_1_MODIFIER_1",
        "AXIS_SLIDER_1_MODIFIER_1_KEY",
        "AXIS_SLIDER_1_MODIFIER_1_COMMAND",
        # HATS
        "POV_1_U_MODIFIERS",
        "POV_1_U_MODIFIER_1",
        "POV_1_UR_MODIFIER_1_KEY",
        "POV_1_UR_MODIFIER_1_COMMAND",
    ]
    test_data = test_string.format(" | ".join(controls))

    rep = replace_unused_keys(test_data)

    assert rep == test_string.format(" | " * (len(controls) - 1))


def test_replace_basic_key_input_string():
    test_string = '<testData>STRING="ABC">{}<testData>'
    controls = [
        ("BUTTON_1", "One"),
        ("AXIS_X", "Two"),
        ("AXIS_SLIDER_1", "Three"),
        ("POV_1_U", "Four"),
        ("POV_1_UR", "Five"),
    ]
    # TODO add scenarios for sanitised values

    for control, string in controls:
        test_data = test_string.format(control)
        rep = replace_input_string(control, string, test_data)
        assert rep == test_string.format(string)


def test_replace_specific_modifier_identifier():
    controls = [
        ("BUTTON_1", 1, Modifier({"ctrl"}, "Modifier 1")),
        ("AXIS_X", 2, Modifier({"ctrl"}, "Modifier 2")),
        ("AXIS_SLIDER_1", 3, Modifier({"ctrl"}, "Modifier 3")),
        ("POV_1_U", 4, Modifier({"ctrl"}, "Modifier 4")),
        ("POV_1_UR", 5, Modifier({"ctrl"}, "Modifier 5")),
    ]

    for control, mod_id, modifier in controls:
        test_case = [
            (
                f"{control}_modifier_{mod_id}",
                f"{modifier.modifiers} - {modifier.command}",
            ),
            (f"{control}_modifier_{mod_id}_key", f"{modifier.modifiers}"),
            (f"{control}_modifier_{mod_id}_action", f"{modifier.command}"),
        ]

        for case, expected in test_case:
            test_string = f'<testData>STRING="ABC">{case}<testData>'
            expected_string = f'<testData>STRING="ABC">{expected}<testData>'
            rep = replace_input_modifier_id_key(control, mod_id, modifier, test_string)
            assert rep == expected_string


def test_replace_input_all_modifiers():
    controls = [
        (
            "BUTTON_1",
            [Modifier({"ctrl"}, "Modifier 1"), Modifier({"alt"}, "Modifier 2")],
        ),
        ("AXIS_X", [Modifier({"ctrl"}, "Modifier 1"), Modifier({"alt"}, "Modifier 2")]),
        (
            "AXIS_SLIDER_1",
            [Modifier({"ctrl"}, "Modifier 1"), Modifier({"alt"}, "Modifier 2")],
        ),
        (
            "POV_1_U",
            [Modifier({"ctrl"}, "Modifier 1"), Modifier({"alt"}, "Modifier 2")],
        ),
        (
            "POV_1_UR",
            [Modifier({"ctrl"}, "Modifier 1"), Modifier({"alt"}, "Modifier 2")],
        ),
    ]

    for control, modifiers in controls:
        test_string = f'<testData>STRING="ABC">{control}_Modifiers<testData>'
        rep = replace_input_modifiers_string(control, modifiers, test_string)

        def build_string(modifiers: list[Modifier]):
            mod_string = ""
            for idx, mod in enumerate(modifiers, 1):
                mod_string = mod_string + f"{str(mod)}"
                if idx != len(modifiers):
                    mod_string = mod_string + " | "
            return mod_string

        expected_string = f'<testData>STRING="ABC">{build_string(modifiers)}<testData>'
        assert rep == expected_string


def test_svg_sanitization():
    tests = [("test", "test")]
    # TODO create test scenarios from DCS data

    for test_value, expected_return in tests:
        assert sanitize_string_for_svg(test_value) == expected_return


@pytest.fixture()
def mock_export_device():
    # Quick dirty object to meet the test, rather than creating a fully valid ExportDevice

    @dataclass
    class MockExportDevice:
        template: "MockTemplate"
        profile_wrapper: "MockWrapper"

    @dataclass
    class MockTemplate:
        raw_data: object

    @dataclass
    class MockWrapper:
        profile_name: str

    obj = MockExportDevice(
        MockTemplate(
            "BUTTON_1 | BUTTON_2 | BUTTON_3 | AXIS_X | POV_1_D | POV_1_U | BUTTON_1_Modifiers"
        ),
        MockWrapper("profile_1"),
    )

    dev = Device_("666ec0a0-556b-11ee-8002-444553540000", "Test Device")

    inputs = [
        (Button(1), "Button Action 1"),
        (Button(2), "Button Action 2"),
        (Axis(AxisDirection.X), "AXIS Control 1"),
        (Hat(1, HatDirection.D), "Hat Control Action 1"),
    ]
    for control, command in inputs:
        dev.create_input(control, command)

    dev.add_modifier_to_input(Button(1), {"ctrl"}, "Modifier 1")

    obj.device = dev

    return obj


def test_template_populate(mock_export_device):
    modified_template = populate_template(mock_export_device)

    assert (
        modified_template
        == "Button Action 1 | Button Action 2 |  | AXIS Control 1 | Hat Control Action 1 |  | Modifier 1 - ctrl"
    )
