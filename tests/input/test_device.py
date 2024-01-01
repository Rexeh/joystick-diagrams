import profile

import pytest

from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.profile import Profile_


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
    pass


def test_device_existing_input(device_obj):
    pass


def test_device_input_single_modifier(device_obj):
    pass


def test_device_input_multi_modifier(device_obj):
    pass
