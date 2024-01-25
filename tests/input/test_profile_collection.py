import pytest

from joystick_diagrams.input_.profile import Profile_
from joystick_diagrams.input_.profile_collection import ProfileCollection


@pytest.fixture
def profile_collection():
    return ProfileCollection()


def test_empty_collection(profile_collection):
    assert profile_collection.profiles == {}


def test_create_profile_in_collection(profile_collection):
    profile_name = "profile1"
    profile_collection.create_profile(profile_name)
    assert profile_name in profile_collection.profiles


def test_profile_object_returned_on_create(profile_collection):
    profile_name = "profile1"
    obj = profile_collection.create_profile(profile_name)

    assert isinstance(obj, Profile_)
    assert obj.name == profile_name


def test_profile_case_insensitivity(profile_collection):
    profile_name = "PROFILE1"
    obj = profile_collection.create_profile(profile_name)

    assert isinstance(obj, Profile_)
    assert obj.name != profile_name
    assert obj.name == profile_name.lower()


def test_get_profile(profile_collection):
    profile_name = "profile1"
    profile_collection.create_profile(profile_name)

    obj = profile_collection.get_profile(profile_name)

    assert obj.name == profile_name

    obj = profile_collection.get_profile(profile_name.upper())

    assert obj.name == profile_name
