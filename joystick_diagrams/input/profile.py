import logging
from copy import deepcopy

from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_

_logger = logging.getLogger("__name__")


class Profile_:
    def __init__(self, profile_name: str):
        self.name: str = profile_name
        self.devices: dict[str, Device_] = {}

    def __repr__(self) -> str:
        return f"(Profile Object: {self.name})"

    def add_device(self, guid: str, name: str) -> Device_:
        guid = Device_.validate_guid(guid)

        if self.get_device(guid) is None:
            self.devices.update({guid: Device_(guid, name)})

        else:
            _logger.warning(f"Device {guid} already exists and will not be re-added")

        return self.get_device(guid)  # type: ignore

    def get_devices(self) -> dict[str, Device_] | None:
        return self.devices

    def get_all_device_guids(self) -> set[str]:
        return {x for x in self.devices.keys()}

    def get_device(self, guid: str) -> Device_ | None:
        return self.devices.get(guid)

    def merge_profiles(self, profile: "Profile_"):
        """Merge Profiles

        Merges the current OBJ with supplied Profile

        OBJ << PROFILE


        """
        src_profile = deepcopy(self)

        for guid, device in profile.devices.items():
            if guid not in src_profile.devices:
                # If the device is not in the current profile, deepcopy the entire device
                src_profile.devices[guid] = deepcopy(device)
            else:
                # If the device exists in the current profile, merge inputs
                existing_device = src_profile.devices[guid]
                for input_type, inputs in device.inputs.items():
                    for input_key, input_ in inputs.items():
                        if input_key not in existing_device.inputs[input_type]:
                            # If the input is not in the existing device, deepcopy the input
                            existing_device.inputs[input_type][input_key] = deepcopy(input_)
                        else:
                            # If the input exists, merge modifiers
                            existing_input = existing_device.inputs[input_type][input_key]
                            for modifier in input_.modifiers:
                                existing_modifier = existing_input._check_existing_modifier(modifier.modifiers)
                                if existing_modifier is None:
                                    existing_input.modifiers.append(deepcopy(modifier))
                                # Don't merge upstream modifier command into current

        return src_profile


if __name__ == "__main__":
    profile1 = Profile_("Profile1")

    dev1 = profile1.add_device("dev_1", "dev_1")
    dev1.create_input(Button(1), "shoot")

    dev1.add_modifier_to_input(Button(1), {"ctrl"}, "bang")
    dev1.add_modifier_to_input(Button(1), {"alt"}, "bang again")

    profile2 = Profile_("Profile2")

    dev3 = profile2.add_device("dev_1", "dev_1")
    dev3.create_input(Button(3), "potato")
    dev3.add_modifier_to_input(Button(1), {"ctrl"}, "hello")

    data = profile1.merge_profiles(profile2)
    print(data)
