import logging
from typing import Optional

from joystick_diagrams.input.device import Device_

_logger = logging.getLogger("__name__")


class Profile_:
    def __init__(self, profile_name: str):
        self.name: str = profile_name
        self.devices: dict[str, Device_] = {}

    def __repr__(self) -> str:
        return f"(Profile Object: {self.name})"

    def add_device(self, guid: str, name: str) -> Device_:
        if self.get_device(guid) is None:
            self.devices.update({guid: Device_(guid, name)})

        else:
            _logger.warning(f"Device {guid} already exists and will not be re-added")

        return self.get_device(guid)  # type: ignore

    def get_device(self, guid: str) -> Device_ | None:
        return self.devices.get(guid)
