"""Handles the creation of Exported items from Joystick Diagrams.

Supplied <DeviceMapping> and list[Profile]

Author: Robert Cox
"""

import html
import logging
import re
from pathlib import Path
from typing import Any

from joystick_diagrams.db.db_device_management import get_device_template_path
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input.profile_collection import ProfileCollection

_logger = logging.getLogger(__name__)


# Exporter
# Extensible to other types of EXPORT destination (svg, pdf)
# Accepts PROFILES
# Users can set the no bind behaviour?
# Users can it to a custom location?
# Dating template re.sub("\\bCURRENT_DATE\\b", datetime.now().strftime("%d/%m/%Y"), template)
# Branding template  re.sub("\\bTEMPLATE_NAME\\b", title, template)

EXPORT_DIRECTORY = ""
ENCODING_TYPE = "utf8"


def export(profile: Profile_, output_directory: Path):
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


def populate_template(template_data: str, device: Device_, profile_name: str) -> str:
    modified_template_data = ""

    # Handle replacement of BUTTONS / AXIS
    # Handle what to do with MODIFIERS for each BUTTON

    return modified_template_data


def read_template(template_path: Path) -> str | None:
    try:
        _logger.debug(f"Reading template data for {template_path}")
        return template_path.read_text(encoding=ENCODING_TYPE)

    except OSError:
        _logger.debug(f"Error reading file data for {template_path}")
        return None


def get_or_create_directory(directory_path: Path):
    pass


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
    # TODO remove mock
    result = get_device_template_path(guid=guid)

    if guid == "dev_2":
        return Path("D:\\Git Repos\\joystick-diagrams\\templates\\CH Fighterstick USB.svg")

    return None


if __name__ == "__main__":
    data = read_template(Path("D:\\Git Repos\\joystick-diagrams\\templates\\CH Fighterstick USB.svg"))

    if data:
        value = "Some bind"
        value = html.escape(value)

        modifiers = ["Modifier1: Do stuff", "Modifier2: Do More Stuff"]
        modifiers.insert(0, value)
        modifiers = [html.escape(x) for x in modifiers]

        insert_value = "<br />".join(modifiers)
        print(insert_value)

        button = "Button_2"
        regex_search = "\\b" + button + "\\b"
        template = re.sub(regex_search, insert_value, data, flags=re.IGNORECASE)

        with open("D:\\Git Repos\\joystick-diagrams\\templates\\Test\\test.svg", "w", encoding="UTF-8") as f:
            f.write(template)

    logging.basicConfig(level=logging.DEBUG)

    collection1 = ProfileCollection()
    profile1 = collection1.create_profile("Profile1")

    dev1 = profile1.add_device("dev_1", "dev_1")
    dev2 = profile1.add_device("dev_2", "dev_2")

    dev1.create_input("input1", "shoot")
    dev2.create_input("input2", "fly")

    dev1.add_modifier_to_input("input1", {"ctrl"}, "bang")
    dev1.add_modifier_to_input("input1", {"alt"}, "bang again")

    export(profile1, Path("D:\\Git Repos\\joystick-diagrams\\diagrams"))
