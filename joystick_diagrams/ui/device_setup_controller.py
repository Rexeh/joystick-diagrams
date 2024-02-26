import logging
from typing import Union

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_device_management import get_device_template_path
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.template import Template

_logger = logging.getLogger(__name__)


def convert_profile_wrappers_to_export_devices(
    profile_wrappers: list[ProfileWrapper],
) -> list[ExportDevice]:
    """Inverts a tree of Profile_ objects to a list of Export Devices"""
    device_map = []

    for wrapper in profile_wrappers:
        for _, device_obj in wrapper.profile.devices.items():
            device_map.append(ExportDevice(device_obj, None, wrapper))

    return device_map


def setup_export_devices(export_device_list: list[ExportDevice]):
    """Configures Export Devices and enriches object with additional information"""
    for export_device in export_device_list:
        # Get the template
        try:
            export_device.template = get_template_for_device(export_device.device_id)
        except JoystickDiagramsError as e:
            _logger.error(e)


def get_export_devices() -> list[ExportDevice]:
    """Retrieves profiles from global state and converts them to device trees"""
    devices = convert_profile_wrappers_to_export_devices(get_processed_profiles())

    setup_export_devices(devices)
    return devices


def get_template_for_device(device_guid: str) -> Union[Template, None]:
    """Retrieves a device template from storage"""
    template = get_device_template_path(device_guid)
    return Template(template) if template else None


def get_processed_profiles() -> list[ProfileWrapper]:
    "Access global state and return processed profiles"
    app_state = AppState()
    return app_state.profile_wrappers


if __name__ == "__main__":
    pass
