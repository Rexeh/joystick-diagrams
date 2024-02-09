from dataclasses import dataclass, field
from typing import Union

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_device_management import get_device_template_path
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.template import Template


@dataclass
class ExportDevice:
    "An ExportDevice packages a given Device_ with its configured Template and origin profile wrapper description."

    device: Device_
    template: Template | None
    description: str
    errors: list = field(default_factory=list, init=False)

    @property
    def device_id(self):
        return self.device.guid

    @property
    def device_name(self):
        return self.device.name

    @property
    def has_template(self) -> bool:
        return bool(self.template)


def convert_profiles_to_export_devices(
    profile_map: dict[str, Profile_],
) -> list[ExportDevice]:
    """Inverts a tree of Profile_ objects to a list of Export Devices"""
    device_map = []

    for profile in profile_map.values():
        for _, device_obj in profile.devices.items():
            device_map.append(ExportDevice(device_obj, None, profile.name))

    return device_map


def setup_export_devices(export_device_list: list[ExportDevice]):
    """Configures Export Devices and enriches object with additional information"""
    for export_device in export_device_list:
        # Get the template
        export_device.template = get_template_for_device(export_device.device_id)


def get_export_devices() -> list[ExportDevice]:
    devices = convert_profiles_to_export_devices(get_processed_profiles())

    setup_export_devices(devices)
    return devices


def get_template_for_device(device_guid: str) -> Union[Template, None]:
    print(f"Getting template for {device_guid}")
    template = get_device_template_path(device_guid)

    print(f"Template was {template}")

    return Template(template) if template else None


def get_processed_profiles():
    app_state = AppState()
    return app_state.get_processed_profiles()


if __name__ == "__main__":
    pass
