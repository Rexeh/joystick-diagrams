import logging

import pytest

from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_

# VALID_GUID = "666EC0A0-556B-11EE-8002-444553540000"


def test_new_device():
    guid = "666ec0a0-556b-11ee-8002-444553540000"
    name = "device name"
    obj = Device_(guid, name)
    assert obj.guid == guid
    assert obj.name == name


def test_new_device_invalid_guid():
    guid = "11ee-8002-444553540000"
    name = "device name"

    with pytest.raises(ValueError, match=f"GUID {guid} is not valid:"):
        Device_(guid, name)


def test_new_device_whitespace():
    guid = "  666ec0a0-556b-11ee-8002-444553540000  "
    name = "   device name  2  "
    obj = Device_(guid, name)
    assert obj.guid == guid.strip()
    assert obj.name == name.strip()


def test_new_device_casing():
    guid = "666EC0A0-556B-11EE-8002-444553540000"
    name = "DEVICE name"
    obj = Device_(guid, name)
    assert obj.guid == guid.lower()
    assert obj.name == name


def test_device_new_input():
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")
    input_id = Button(1)
    operation = "Press"

    assert obj.inputs["buttons"] == {}
    obj.create_input(input_id, operation)

    assert obj.inputs["buttons"]["BUTTON_1"]


def test_new_modifier():
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")
    input_id = Button(1)
    operation = "Press"
    obj.create_input(input_id, operation)
    obj.add_modifier_to_input(input_id, {"alt"}, "press")

    input_ = obj.get_input("buttons", input_id.identifier)
    assert len(input_.modifiers) > 0
    assert input_.modifiers[0].modifiers == {"alt"}
    assert input_.modifiers[0].command == "press"


def test_existing_modifier():
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")
    input_id = Button(1)
    operation = "Press"
    obj.create_input(input_id, operation)

    obj.add_modifier_to_input(input_id, {"ctrl"}, "One")
    obj.add_modifier_to_input(input_id, {"ctrl"}, "Two")

    input_ = obj.get_input("buttons", input_id.identifier)

    assert len(input_.modifiers) == 1
    assert input_.modifiers[0].command == "Two"


def test_device_existing_input(caplog):
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")
    input_id = Button(1)
    operation = "Press"
    obj.create_input(input_id, operation)
    obj.create_input(input_id, "modified")

    input_ = obj.get_input("buttons", input_id.identifier)

    assert input_.identifier == input_id.identifier
    assert input_.command == "modified"


def test_new_modifier_no_input(caplog):
    caplog.set_level(logging.DEBUG)
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")
    obj.add_modifier_to_input(Button(1), {"alt"}, "press")

    assert (
        "Modifier attempted to be added to Button(id=1) but input does not exist"
        in caplog.text
    )


def test_resolve_type():
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")
    with pytest.raises(ValueError):
        obj.resolve_type(control=Button)


def test_combined_inputs():
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")
    expected_len = 2
    button_1 = Button(1)
    obj.create_input(button_1, "Shoot")
    obj.create_input(Button(44), "Shoot")

    flattened = obj.get_combined_inputs()

    assert flattened.__len__() == expected_len
    assert flattened["BUTTON_1"].input_control == button_1


def test_get_inputs():
    obj = Device_("666EC0A0-556B-11EE-8002-444553540000", "name")

    obj.create_input(Button(1), "Shoot")
    obj.create_input(Button(44), "Shoot")

    all_inputs = obj.get_inputs()
    expected_keys = ("buttons", "axis", "axis_slider", "hats")
    assert [x for x in expected_keys if x in all_inputs.keys()]
