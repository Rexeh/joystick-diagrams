# Test creation of new devicew
# Test duplication of new device is prevented
# Check a device can have an input registered
# Check a device can have an input overwritten
import logging
from joystick_diagrams.classes.input import (
    add_device,
    LogicalDevice,
    InputTypes,
    Command,
    add_inputs,
    add_input_modifier,
    get_devices,
    clear_devices,
)

LOGGER = logging.getLogger(__name__)


def setup_function():
    add_device("dev-1", "device 1")
    add_device("dev-2", "device 2")


def test_add_device():
    guid = "test_guid"
    name = "test_name"
    add_device(guid, name)
    devices = get_devices()
    assert len(devices), 1
    assert devices[guid].guid, guid
    assert devices[guid].name, name


def test_check_devices_registered():
    devices = get_devices()
    assert "dev-1" in devices
    assert "dev-2" in devices


def test_clear_devices():
    assert len(get_devices()) > 0
    clear_devices()
    assert len(get_devices()) == 0


def test_check_devices_duplication_name(caplog):
    device = add_device("dev-1", "device XYZ")
    assert device.guid == "dev-1"
    assert device.name == "device 1"
    assert isinstance(device, LogicalDevice), LogicalDevice
    assert "Device dev-1 already exists and will not be re-added" in caplog.text


# Test for correct behaviour
# Add an input
# Moodify an input (overwrtite)
# Add modifiers to an existing input (but original input not changed)


def test_add_multiple_inputs_with_modifiers():
    # TO DO > Setup in fixture
    guid = "dev-1"
    # Define the inputs and modifiers
    inputs = [
        {"id": "input1", "style": InputTypes.BUTTON, "command": Command("command1")},
        {"id": "input2", "style": InputTypes.AXIS, "command": Command("command2")},
    ]
    modifiers = [
        {"input": {"modifier1"}, "command": Command("modifier_command1")},
        {"input": {"modifier2"}, "command": Command("modifier_command2")},
    ]

    # Add the inputs and modifiers to the device
    for input_data in inputs:
        add_inputs(guid, input_id=input_data["id"], style=input_data["style"], command=input_data["command"])
        for modifier_data in modifiers:
            add_input_modifier(guid, input_data["id"], modifier_data["input"], modifier_data["command"])

    # Retrieve the inputs from the device
    device_inputs = get_devices(guid).get_device_inputs()

    # Check that the correct number of inputs were added
    assert len(device_inputs), len(inputs)

    # Check that each input has the correct properties
    for input_data in inputs:
        input = next((x for x in device_inputs if x.identifier == input_data["id"]), None)
        assert input, None
        assert input.style, input_data["style"]
        assert input.command.name, input_data["command"].name

        # Check that each input has the correct modifiers
        for modifier_data in modifiers:
            modifier = next((x for x in input.modifiers if x.modifiers == modifier_data["input"]), None)
            assert modifier, None
            assert modifier.command.name, modifier_data["command"].name


def test_add_modify_existing_modifier():
    # TO DO > Setup in fixture
    guid = "dev-1"
    # Define the inputs and modifiers
    inputs = [
        {"id": "input1", "style": InputTypes.BUTTON, "command": Command("command1")},
        {"id": "input2", "style": InputTypes.AXIS, "command": Command("command2")},
    ]
    modifiers = [
        {"input": {"modifier1"}, "command": Command("modifier_command1")},
        {"input": {"modifier2"}, "command": Command("modifier_command2")},
    ]

    # Add the inputs and modifiers to the device
    for input_data in inputs:
        add_inputs(guid, input_id=input_data["id"], style=input_data["style"], command=input_data["command"])
        for modifier_data in modifiers:
            add_input_modifier(guid, input_data["id"], modifier_data["input"], modifier_data["command"])

    # Retrieve the inputs from the device
    device_inputs = get_devices(guid).get_device_inputs()

    # Check that each input has the correct properties
    for input_data in inputs:
        input = next((x for x in device_inputs if x.identifier == input_data["id"]), None)
        assert input, None
        assert input.style, input_data["style"]
        assert input.command.name, input_data["command"].name

        # Check that each input has the correct modifiers
        for modifier_data in modifiers:
            modifier = next((x for x in input.modifiers if x.modifiers == modifier_data["input"]), None)
            assert modifier, None
            assert modifier.command.name, modifier_data["command"].name

    # Change a modifier
    device = get_devices(guid)
    add_input_modifier(guid, "input1", {"modifier1"}, "potato")
    assert device.inputs[0].modifiers[0].command == "potato"
