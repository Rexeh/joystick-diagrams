"""Tests for GUID alias resolution integration in AppState."""

from unittest.mock import patch

import pytest

from joystick_diagrams.conflict_strategy import AliasConflictStrategy
from joystick_diagrams.db.device_alias_service import DeviceAliasService
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_

GUID_A = "aaaa0000-0000-0000-0000-000000000001"
GUID_B = "bbbb0000-0000-0000-0000-000000000002"
GUID_C = "cccc0000-0000-0000-0000-000000000003"


@pytest.fixture()
def alias_service_no_aliases():
    """DeviceAliasService with no aliases configured."""
    with patch(
        "joystick_diagrams.db.device_alias_service.db_device_aliases"
    ) as mock_db:
        mock_db.get_all_aliases.return_value = []
        yield DeviceAliasService()


@pytest.fixture()
def alias_service_a_to_b():
    """DeviceAliasService with GUID_A -> GUID_B alias."""
    with patch(
        "joystick_diagrams.db.device_alias_service.db_device_aliases"
    ) as mock_db:
        mock_db.get_all_aliases.return_value = [(GUID_A, GUID_B)]
        yield DeviceAliasService()


def _make_profile_with_device(name, guid, device_name, buttons=None):
    """Helper: create a profile with one device, optionally adding button inputs."""
    profile = Profile_(name)
    device = profile.add_device(guid, device_name)
    for btn_id, command in buttons or []:
        device.create_input(Button(btn_id), command)
    return profile


class TestApplyAliasesToProfile:
    """Tests for AppState._apply_aliases_to_profile static method."""

    def test_no_aliases_device_stays_under_original_guid(
        self, alias_service_no_aliases
    ):
        """When there are no aliases, the device stays under its original GUID."""
        from joystick_diagrams.app_state import AppState

        profile = _make_profile_with_device(
            "test", GUID_A, "DeviceA", buttons=[(1, "fire")]
        )

        result = AppState._apply_aliases_to_profile(profile, alias_service_no_aliases)

        assert GUID_A in result.devices
        assert len(result.devices) == 1

    def test_alias_present_device_rekeyed_under_target_guid(self, alias_service_a_to_b):
        """When an alias exists, the device is rekeyed under the target GUID
        and device.guid is updated."""
        from joystick_diagrams.app_state import AppState

        profile = _make_profile_with_device(
            "test", GUID_A, "DeviceA", buttons=[(1, "fire")]
        )

        result = AppState._apply_aliases_to_profile(profile, alias_service_a_to_b)

        assert GUID_A not in result.devices
        assert GUID_B in result.devices
        assert result.devices[GUID_B].guid == GUID_B
        assert len(result.devices) == 1

    def test_source_and_target_conflict_concatenate_strategy(
        self, alias_service_a_to_b
    ):
        """CONCATENATE strategy: source's primary is written first, joined with
        the target's primary via the concatenation separator. Non-conflicting
        inputs gap-fill unchanged."""
        from joystick_diagrams.app_state import AppState

        profile = Profile_("test")
        # Target device (GUID_B) with button 1 = "missile"
        dev_b = profile.add_device(GUID_B, "DeviceB")
        dev_b.create_input(Button(1), "missile")
        # Source device (GUID_A) with button 1 = "fire" and button 2 = "flare"
        dev_a = profile.add_device(GUID_A, "DeviceA")
        dev_a.create_input(Button(1), "fire")
        dev_a.create_input(Button(2), "flare")

        result = AppState._apply_aliases_to_profile(
            profile, alias_service_a_to_b, strategy=AliasConflictStrategy.CONCATENATE
        )

        assert GUID_A not in result.devices
        assert GUID_B in result.devices
        merged = result.devices[GUID_B]
        # Source-wins-primary: "fire" appears first, target "missile" appended
        # with its device-name as a bracketed qualifier so the user can see
        # where the loser segment came from.
        assert (
            merged.inputs["buttons"]["BUTTON_1"].command == "fire | [DeviceB] missile"
        )
        # Gap-fill: button 2 comes from source.
        assert merged.inputs["buttons"]["BUTTON_2"].command == "flare"

    def test_source_and_target_conflict_modifier_strategy(self, alias_service_a_to_b):
        """MODIFIER strategy: source's primary wins; target's primary is promoted
        to a Modifier keyed by the target device's name."""
        from joystick_diagrams.app_state import AppState

        profile = Profile_("test")
        dev_b = profile.add_device(GUID_B, "DeviceB")
        dev_b.create_input(Button(1), "missile")
        dev_a = profile.add_device(GUID_A, "DeviceA")
        dev_a.create_input(Button(1), "fire")

        result = AppState._apply_aliases_to_profile(
            profile, alias_service_a_to_b, strategy=AliasConflictStrategy.MODIFIER
        )

        merged = result.devices[GUID_B]
        input_ = merged.inputs["buttons"]["BUTTON_1"]
        assert input_.command == "fire"
        assert len(input_.modifiers) == 1
        assert input_.modifiers[0].command == "missile"
        assert input_.modifiers[0].modifiers == {"DeviceB"}

    def test_unaliased_devices_pass_through_unchanged(self, alias_service_a_to_b):
        """Devices with GUIDs that have no alias pass through unchanged."""
        from joystick_diagrams.app_state import AppState

        profile = _make_profile_with_device(
            "test", GUID_C, "DeviceC", buttons=[(5, "eject")]
        )

        result = AppState._apply_aliases_to_profile(profile, alias_service_a_to_b)

        assert GUID_C in result.devices
        assert result.devices[GUID_C].guid == GUID_C
        assert result.devices[GUID_C].inputs["buttons"]["BUTTON_5"].command == "eject"

    def test_alias_with_target_existing_merged_device_has_inputs_from_both(
        self, alias_service_a_to_b
    ):
        """After merging, the resulting device has inputs from both source and target."""
        from joystick_diagrams.app_state import AppState

        profile = Profile_("test")
        dev_b = profile.add_device(GUID_B, "DeviceB")
        dev_b.create_input(Button(1), "missile")
        dev_a = profile.add_device(GUID_A, "DeviceA")
        dev_a.create_input(Button(2), "flare")
        dev_a.create_input(Button(3), "chaff")

        result = AppState._apply_aliases_to_profile(profile, alias_service_a_to_b)

        merged = result.devices[GUID_B]
        # All three buttons should be present
        assert "BUTTON_1" in merged.inputs["buttons"]
        assert "BUTTON_2" in merged.inputs["buttons"]
        assert "BUTTON_3" in merged.inputs["buttons"]
        assert merged.inputs["buttons"]["BUTTON_1"].command == "missile"
        assert merged.inputs["buttons"]["BUTTON_2"].command == "flare"
        assert merged.inputs["buttons"]["BUTTON_3"].command == "chaff"
