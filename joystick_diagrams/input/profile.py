import logging
from copy import deepcopy

from joystick_diagrams.conflict_strategy import (
    InheritanceConflictStrategy,
    apply_input_conflict,
)
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input_routing import RouteKey, RouteTarget

_logger = logging.getLogger("__name__")


class Profile_:  # noqa: N801
    def __init__(self, profile_name: str):
        self.name: str = profile_name
        self.devices: dict[str, Device_] = {}
        self.input_routes: dict[RouteKey, list[RouteTarget]] = {}

    def __repr__(self) -> str:
        return f"(Profile Object: {self.name})"

    def add_device(self, guid: str, name: str) -> Device_:
        guid = Device_.validate_guid(guid)

        if self.get_device(guid) is None:
            self.devices.update({guid: Device_(guid, name)})

        else:
            _logger.warning(f"Device {guid} already exists and will not be re-added")

        return self.devices[guid]

    def get_devices(self) -> dict[str, Device_] | None:
        return self.devices

    def get_device(self, guid: str) -> Device_ | None:
        return self.devices.get(guid)

    def merge_profiles(
        self,
        profile: "Profile_",
        strategy: InheritanceConflictStrategy = InheritanceConflictStrategy.KEEP_EXISTING,
    ):
        """Merge Profiles

        Merges the current OBJ with supplied Profile

        OBJ << PROFILE

        `strategy` controls primary-binding conflict handling; see
        `conflict_strategy.apply_input_conflict`. Loser qualifier is the parent
        profile's `name` (used for promoted modifiers under MODIFIER strategy).
        """
        src_profile = deepcopy(self)

        for guid, device in profile.devices.items():
            _logger.debug(f"Handling {guid=} and {device=}")
            if guid not in src_profile.devices:
                _logger.debug(f"Device {guid=} not found so adding whole device")
                src_profile.devices[guid] = deepcopy(device)
                continue

            existing_device = src_profile.devices[guid]
            for input_type, inputs in device.inputs.items():
                for input_key, input_ in inputs.items():
                    if input_key not in existing_device.inputs[input_type]:
                        existing_device.inputs[input_type][input_key] = deepcopy(input_)
                    else:
                        apply_input_conflict(
                            winner=existing_device.inputs[input_type][input_key],
                            loser=input_,
                            loser_qualifier=profile.name,
                            strategy=strategy,
                        )

        return src_profile


if __name__ == "__main__":
    pass
