from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_


def test_merge_empty_profiles():
    profile_1 = Profile_("Profile_1")
    profile_2 = Profile_("Profile_1")

    merged_instance = profile_1.merge_profiles(profile_2)

    assert profile_1.name == "Profile_1"
    assert merged_instance != profile_1


def test_merge_device_into_profile():
    profile_1 = Profile_("Profile_1")
    profile_2 = Profile_("Profile_1")

    assert profile_1.devices.__len__() == 0

    profile_2.add_device("guid", "guid")

    merged_instance = profile_1.merge_profiles(profile_2)

    assert profile_1.name == "Profile_1"
    assert merged_instance.name == "Profile_1"

    assert merged_instance.devices.__len__() == 1


def test_merge_device_into_profile_with_same_inputs():
    """Checks that the primary instance command values take precedent (I.e. overwrite the profile being merged)"""
    # Profile 1 Setup
    profile_1 = Profile_("Profile_1")
    profile_1_dev = profile_1.add_device("guid1", "guid")
    profile_1_dev.create_input(Button(1), "First")

    #  Profile 2  Setup
    profile_2 = Profile_("Profile_1")
    profile_2_dev = profile_2.add_device("guid1", "guid")
    profile_2_dev.create_input(Button(1), "Second")

    merged_instance = profile_1.merge_profiles(profile_2)

    assert merged_instance.devices.__len__() == 1
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].command == "First"


def test_merge_device_into_profile_with_different_inputs():
    """Checks that the primary instance can gain a new input previously not existing the merge target"""
    # Profile 1 Setup
    profile_1 = Profile_("Profile_1")
    profile_1_dev = profile_1.add_device("guid1", "guid")
    profile_1_dev.create_input(Button(1), "First")

    #  Profile 2  Setup
    profile_2 = Profile_("Profile_1")
    profile_2_dev = profile_2.add_device("guid1", "guid")
    profile_2_dev.create_input(Button(2), "Second")

    merged_instance = profile_1.merge_profiles(profile_2)

    assert merged_instance.devices.__len__() == 1
    assert merged_instance.devices["guid1"].inputs["buttons"].__len__() == 2
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].command == "First"
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_2"].command == "Second"


def test_merge_device_into_profile_with_modifier_from_target():
    """Checks that the primary instance existing input can inherit a new modifier from target"""
    # Profile 1 Setup
    profile_1 = Profile_("Profile_1")
    profile_1_dev = profile_1.add_device("guid1", "guid")
    profile_1_dev.create_input(Button(1), "First")

    #  Profile 2  Setup
    profile_2 = Profile_("Profile_1")
    profile_2_dev = profile_2.add_device("guid1", "guid")
    profile_2_dev.create_input(Button(1), "Second")
    profile_2_dev.add_modifier_to_input(Button(1), {"ctrl"}, "Modifier")

    merged_instance = profile_1.merge_profiles(profile_2)

    assert merged_instance.devices.__len__() == 1
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].command == "First"
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].modifiers.__len__() == 1
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].modifiers[0].command == "Modifier"
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].modifiers[0].modifiers == {"ctrl"}


def test_merge_device_into_profile_with_existing_merged_with_target():
    """Checks that the primary instance existing input can inherit a new modifier from target"""
    # Profile 1 Setup
    profile_1 = Profile_("Profile_1")
    profile_1_dev = profile_1.add_device("guid1", "guid")
    profile_1_dev.create_input(Button(1), "First")
    profile_1_dev.add_modifier_to_input(Button(1), {"ctrl"}, "Modifier")

    #  Profile 2  Setup
    profile_2 = Profile_("Profile_1")
    profile_2_dev = profile_2.add_device("guid1", "guid")
    profile_2_dev.create_input(Button(1), "Second")
    profile_2_dev.add_modifier_to_input(Button(1), {"ctrl"}, "OtherModifier")

    merged_instance = profile_1.merge_profiles(profile_2)

    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].modifiers[0].command == "Modifier"
    assert merged_instance.devices["guid1"].inputs["buttons"]["BUTTON_1"].modifiers[0].modifiers == {"ctrl"}
