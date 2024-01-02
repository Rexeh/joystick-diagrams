import profile

import pytest

from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.profile import Profile_


@pytest.fixture()
def profile_obj():
    def _profile_object(profile_name: str):
        return Profile_(profile_name)

    return _profile_object


def test_profile_creation(profile_obj):
    assert profile_obj("profile1").name == "profile1"


def test_profile_device(profile_obj):
    guid = "DEVICE_GUID_1"
    device_name = "DEVICE 1"
    obj = profile_obj("profile1")
    new_device = obj.add_device(guid, device_name)

    assert guid.lower() in obj.devices
    assert isinstance(new_device, Device_)


def test_duplicate_device(profile_obj, caplog):
    guid_1 = "ABC"
    guid_2 = "abc"

    profile = profile_obj("profile1")

    profile.add_device(guid_1, "")
    profile.add_device(guid_2, "")

    assert len(profile.devices) == 1
    assert f"Device {guid_1.lower()} already exists and will not be re-added" in caplog.text
