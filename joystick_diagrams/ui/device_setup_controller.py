import logging
from typing import Union

from joystick_diagrams.app_state import AppState
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.template import Template
from joystick_diagrams.template_identity import (
    TemplateResolution,
    relink_device_template,
)

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
        resolution = resolve_device_template(export_device.device_id)
        export_device.template_missing = resolution.status == "missing"
        try:
            export_device.template = template_from_resolution(
                resolution, template_cache
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


def resolve_device_template(device_guid: str) -> TemplateResolution:
    """Where the controller's chosen template is now.

    ``status`` is ``"none"`` (no template chosen), ``"ok"``, ``"relinked"`` (the
    file moved and was found again by name or sha256; the row and its layout
    edits now point at the new path) or ``"missing"``. A missing template is
    reported, never removed: the Export list and stage 2 show it with
    "Choose template…" instead.
    """
    state = AppState()
    return relink_device_template(
        device_guid, state.device_service, state.layout_service
    )


def template_from_resolution(
    resolution: TemplateResolution,
    cache: dict[str, Template | None] | None = None,
) -> Template | None:
    if not resolution.usable or resolution.path is None:
        return None
    template_path = str(resolution.path)
    if cache is not None and template_path in cache:
        return cache[template_path]
    result = Template(template_path)
    if cache is not None:
        cache[template_path] = result
    return result


def get_template_for_device(
    device_guid: str,
    cache: dict[str, Template | None] | None = None,
) -> Union[Template, None]:
    """Retrieves a device template from storage (``None`` when unchosen or missing)."""
    return template_from_resolution(resolve_device_template(device_guid), cache)


def get_processed_profiles() -> list[ProfileWrapper]:
    "Access global state and return processed profiles"
    app_state = AppState()
    return app_state.profile_wrappers


if __name__ == "__main__":
    pass
