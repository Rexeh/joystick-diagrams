import logging
from pathlib import Path
from typing import Union

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_device_management import (
    get_device_template_path,
    remove_template_path_from_device,
)
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
    template_cache: dict[str, Template | None] = {}

    for export_device in export_device_list:
        try:
            export_device.template = get_template_for_device(
                export_device.device_id, template_cache
            )
        except JoystickDiagramsError as e:
            _logger.error(e)


def get_export_devices() -> list[ExportDevice]:
    """Retrieves profiles from global state and converts them to device trees"""
    devices = convert_profile_wrappers_to_export_devices(get_processed_profiles())

    # Filter out hidden devices
    app_state = AppState()
    devices = [
        d for d in devices if not app_state.device_service.is_hidden(d.device_id)
    ]

    setup_export_devices(devices)
    return devices


def get_template_for_device(
    device_guid: str,
    cache: dict[str, Template | None] | None = None,
) -> Union[Template, None]:
    """Retrieves a device template from storage"""
    template_path = get_device_template_path(device_guid)

    if not template_path:
        return None

    # Return cached Template if available
    if cache is not None and template_path in cache:
        return cache[template_path]

    exists = Path(template_path).exists()

    if not exists:
        _logger.warning(
            f"Template was retrieved for {device_guid} resulting in {template_path} but item doesn't exist at the path so it will be removed from database"
        )
        remove_template_path_from_device(device_guid)
        result = None
    else:
        result = Template(template_path)

    if cache is not None:
        cache[template_path] = result

    return result


def get_processed_profiles() -> list[ProfileWrapper]:
    "Access global state and return processed profiles"
    app_state = AppState()
    return app_state.profile_wrappers


if __name__ == "__main__":
    pass
