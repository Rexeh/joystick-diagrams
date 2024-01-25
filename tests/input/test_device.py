import pytest

from joystick_diagrams.input_.device import Device_


@pytest.fixture()
def device_obj():
    def _device_obj(guid: str, name: str):
        return Device_(guid, name)

    return _device_obj


def test_new_device(device_obj):
    guid = "guid1"
    name = "device name"
    obj = device_obj(guid, name)
    assert obj.guid == guid
    assert obj.name == name


def test_new_device_whitespace(device_obj):
    guid = "   guid     1    "
    name = "   device name  2  "
    obj = device_obj(guid, name)
    assert obj.guid == guid.strip()
    assert obj.name == name.strip()


def test_new_device_casing(device_obj):
    guid = "GUID-1"
    name = "DEVICE name"
    obj = device_obj(guid, name)
    assert obj.guid == guid.lower()
    assert obj.name == name


def test_device_new_input(device_obj):
    obj = device_obj("guid", "name")
    input_id = "BUTTON_1"
    operation = "Press"
    obj.create_input(input_id, operation)

    input = obj.get_input(input_id)

    assert input.identifier == input_id.lower()
    assert input.command == operation


def test_new_modifier(device_obj):
    obj = device_obj("guid", "name")
    input_id = "BUTTON_1"
    operation = "Press"
    obj.create_input(input_id, operation)
    obj.add_modifier_to_input(input_id, {"alt"}, "press")

    input = obj.get_input(input_id)
    assert len(input.modifiers) > 0
    assert input.modifiers[0].modifiers == {"alt"}
    assert input.modifiers[0].command == "press"


def test_existing_modifier(device_obj):
    obj = device_obj("guid", "name")
    input_id = "BUTTON_1"
    operation = "Press"
    obj.create_input(input_id, operation)

    obj.add_modifier_to_input(input_id, {"ctrl"}, "One")
    obj.add_modifier_to_input(input_id, {"ctrl"}, "Two")

    input = obj.get_input(input_id)

    assert len(input.modifiers) == 1
    assert input.modifiers[0].command == "Two"


def test_device_existing_input(device_obj, caplog):
    obj = device_obj("guid", "name")
    input_id = "BUTTON_1"
    operation = "Press"
    obj.create_input(input_id, operation)
    obj.create_input(input_id, "modified")

    input = obj.get_input(input_id)

    assert input.identifier == input_id.lower()
    assert input.command == "modified"


def test_new_modifier_no_input(device_obj, caplog):
    obj = device_obj("guid", "name")
    obj.add_modifier_to_input("non_existing_input", {"alt"}, "press")

    assert "Modifier attempted to be added to non_existing_input but input does not exist" in caplog.text
