"""Handles the creation of Exported items from Joystick Diagrams.

Supplied <DeviceMapping> and list[Profile]

Author: Robert Cox
"""

import json
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

DEVICE_FILE_PATH = Path("./data/devices.json")


class DeviceManager:
    def __init__(self):
        self.devices: dict[str, str | None] = {}
        self.load_from_file()

    def add_device(self, guid: str, svg_path: str) -> None:
        """Add device to the device list with a valid path."""
        if self.validate_template_path(svg_path):
            self.devices[guid] = svg_path
        self.save_to_file()

    def validate_template_path(self, file_path: str | None) -> bool:
        """Validates the template is a valid file."""

        _logger.debug(f"Validating path {file_path}")
        if file_path:
            return Path(file_path).is_file()
        return False

    def save_to_file(self):
        with open(DEVICE_FILE_PATH, "w") as f:
            json.dump(self.devices, f)

    def load_from_file(self):
        try:
            with open(DEVICE_FILE_PATH, "r") as f:
                self.devices = json.load(f)
                _save = False
                # Validate the paths are still valid
                for device, path in self.devices.items():
                    if not path:
                        continue

                    _check = self.validate_template_path(path)
                    _logger.debug(f"Validating: {device} is {_check}")

                    if not _check:
                        self.devices[device] = None
                        _logger.debug(f"{device} path is invalid {_check}")
                        _save = True

                if _save:
                    self.save_to_file()

                _logger.debug(f"Device mappings loaded are: {self.devices}")
        except FileNotFoundError:
            self.devices = {}


# Exporter
# Extensible to other types of EXPORT destination (svg, pdf)


# mapping = DeviceMap(
#     map={
#         "guid1": Path("D:\\Git Repos\\joystick-diagrams\\templates\\CH Fighterstick USB.svg"),
#         "guid2": Path("D:\\Git Repos\\joystick-diagrams\\templates\\CH Fighterstick USB.svg"),
#     }
# )


class Exporter:
    def __init__(self, device_map: DeviceManager):
        pass


dm = DeviceManager()

dm.add_device("192912921", "D:\\Git Repos\\joystick-diagrams\\templates\\CH Fighterstick USB.svg")
print(dm.devices)
