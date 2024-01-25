"""Handles the creation of Exported items from Joystick Diagrams.

Supplied <DeviceMapping> and list[Profile]

Author: Robert Cox
"""

import html
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from joystick_diagrams.db.db_device_management import get_device_template_path
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.profile import Profile_

_logger = logging.getLogger(__name__)


# Exporter
# Extensible to other types of EXPORT destination (svg, pdf)
# Accepts PROFILES
# Users can set the no bind behaviour?
# Users can it to a custom location?
# Dating template re.sub("\\bCURRENT_DATE\\b", datetime.now().strftime("%d/%m/%Y"), template)
# Branding template  re.sub("\\bTEMPLATE_NAME\\b", title, template)

EXPORT_DIRECTORY = Path.joinpath(Path(os.path.dirname(__file__)).parent, "test_export")
ENCODING_TYPE = "utf8"


def export(profile: Profile_, output_directory: Path = EXPORT_DIRECTORY):
    try:
        profile_name = profile.name

        # Get Profile Devices, that have valid templates
        _logger.debug(f"Getting device templates for {profile} object")
        export_devices = get_profile_device_templates(profile.devices)

        # Use the template
        export_devices_to_templates(export_devices, profile_name)
        # Iterate over the DEVICE items to format the template
        # Check output directory exists

        pass
    except Exception as e:
        _logger.debug(e)


def export_devices_to_templates(devices: dict[str, dict[str, Any]], profile_name: str):
    """Handles the manipulation of the template."""
    for _, device_data in devices.items():
        _obj = device_data["Object"]
        _template = device_data["Template"]
        # Get the template
        raw_template_data = read_template(_template)

        if raw_template_data is None:
            _logger.error(f"There was an issue getting data for the current template: {_template}")
            continue

        # Replace strings in the template data with device data
        result = populate_template(raw_template_data, _obj, profile_name)

        # TODO hardcode for test
        file_name = f"{_obj.name}-{profile_name}.svg"
        save_template(result, file_name)


def create_directory_if_not_exists(directory: Path):
    if directory.exists():
        return

    Path.mkdir(directory)


def save_template(template_data, file_name):
    create_(EXPORT_DIRECTORY)
    with open(EXPORT_DIRECTORY.joinpath(file_name), "w", encoding="UTF-8") as f:
        f.write(template_data)


def populate_template(template_data: str, device: Device_, profile_name: str) -> str:
    modified_template_data = template_data

    # TODO improve boilerplate for test
    for input_key, input_object in device.get_combined_inputs().items():
        template_key = input_key

        # Escape the primary action
        primary_action = html.escape(input_object.command)

        # Create Modifier Strings
        mod_string = ""
        for modifier in input_object.modifiers:
            mod_string = mod_string + "<br />" + html.escape(modifier.__str__())

        modifiers = input_object.modifiers.__str__()
        final_template_string = primary_action + mod_string

        regex_search = "\\b" + template_key + "\\b"
        modified_template_data = re.sub(
            regex_search, final_template_string, modified_template_data, flags=re.IGNORECASE
        )

    return modified_template_data


def read_template(template_path: Path) -> str | None:
    try:
        _logger.debug(f"Reading template data for {template_path}")
        return template_path.read_text(encoding=ENCODING_TYPE)

    except OSError:
        _logger.debug(f"Error reading file data for {template_path}")
        return None


def get_profile_device_templates(devices: dict[str, Device_]) -> dict[str, Device_ | Path]:
    filtered_devices: dict = {}
    for device_name, device_obj in devices.items():
        lookup = get_template_for_device(device_obj.guid)

        if lookup is None:
            _logger.info(f"No template configured for {device_name}")
            continue

        filtered_devices[device_name] = {"Object": device_obj, "Template": lookup}

    return filtered_devices


def get_template_for_device(guid: str) -> Path | None:
    # result = get_device_template_path(guid=guid)

    TEST_FILE_LOC = Path.joinpath(Path(os.path.dirname(__file__)).parent, "test_devices.json")

    json_data = TEST_FILE_LOC.read_text()

    test_config = dict(json.loads(json_data))

    template = test_config.get(guid)

    if template:
        return Path(template)

    return None


if __name__ == "__main__":
    # data = read_template(Path("D:\\Git Repos\\joystick-diagrams\\templates\\CH Fighterstick USB.svg"))

    # logging.basicConfig(level=logging.DEBUG)

    # collection1 = ProfileCollection()
    # profile1 = collection1.create_profile("Profile1")

    # dev1 = profile1.add_device("dev_1", "dev_1")
    # dev2 = profile1.add_device("dev_2", "dev_2")

    # dev1.create_input(Button(1), "shoot")
    # dev2.create_input(Button(2), "fly")

    # dev1.add_modifier_to_input(Button(1), {"ctrl"}, "bang")
    # dev1.add_modifier_to_input(Button(1), {"alt"}, "bang again")

    # export(profile1, Path("D:\\Git Repos\\joystick-diagrams\\diagrams"))
    get_template_for_device("abd")
