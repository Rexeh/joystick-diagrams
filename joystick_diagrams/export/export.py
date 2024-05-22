"""Handles the creation of Exported items from Joystick Diagrams.

Supplied <DeviceMapping> and list[Profile]

Author: Robert Cox
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape, unescape

from joystick_diagrams import utils
from joystick_diagrams.export.export_device import ExportDevice
from joystick_diagrams.input.modifier import Modifier
from joystick_diagrams.template import Template

_logger = logging.getLogger(__name__)

TEMPLATE_NAMING_KEY = "TEMPLATE_NAME"
TEMPLATE_DATING_KEY = "CURRENT_DATE"


def export(export_device: ExportDevice, output_directory: str):
    try:
        export_device_to_templates(export_device, Path(output_directory))

    except Exception as e:
        _logger.debug(e)


def export_device_to_templates(export_device: ExportDevice, export_location: Path):
    """Handles the manipulation of the template."""

    if export_device.template is None:
        _logger.error(
            f"There was an issue getting data for the current template: {export_device}"
        )
        return

    # Replace strings in the template data with device data
    result = populate_template(export_device)

    # TODO handle duplicate file names due to device name clashes
    file_name = f"{export_device.device_id[:5]}-{export_device.device.name}-{export_device.profile_wrapper.profile_name}.svg"
    save_template(result, file_name, export_location)


def save_template(template_data, file_name, export_path):
    utils.create_directory(export_path)

    with open(export_path.joinpath(file_name), "w", encoding="UTF-8") as f:
        f.write(template_data)


def populate_template(export_device: ExportDevice) -> str:
    """Manipulates template_data to replace known keys with data from Device_"""
    modified_template_data = export_device.template.raw_data

    for input_key, input_object in export_device.device.get_combined_inputs().items():
        modified_template_data = replace_input_string(
            input_key,
            sanitize_string_for_svg(input_object.command),
            modified_template_data,
        )

        if input_object.modifiers:
            modified_template_data = replace_input_modifiers_string(
                input_key, input_object.modifiers, modified_template_data
            )

            for modifier_number, modifier in enumerate(input_object.modifiers, 1):
                modified_template_data = replace_input_modifier_id_key(
                    input_key, modifier_number, modifier, modified_template_data
                )

    modified_template_data = replace_template_name_string(
        export_device.profile_wrapper.profile_name, modified_template_data
    )

    modified_template_data = replace_template_date_string(modified_template_data)

    modified_template_data = replace_unused_keys(modified_template_data)

    return modified_template_data


def sanitize_string_for_svg(value_to_sanitize: str) -> str:
    """Safely sanitize string for SVG display"""
    return escape(unescape(value_to_sanitize))


def replace_input_modifiers_string(
    input_key: str, modifiers: list[Modifier], data: str
) -> str:
    """Replaces the INPUT_KEY_MODIFIERS key with combined modifiers from input"""
    search = re.compile(rf"\b{input_key}_Modifiers\b", re.IGNORECASE)

    # Create Modifier Strings
    mod_string = ""
    total_modifiers = len(modifiers)
    for modifier_index, modifier in enumerate(modifiers, 1):
        mod_string = mod_string + sanitize_string_for_svg(str(modifier))

        # Due to way SVG handles new lines, this is a compromise for modifiers to be joined and look reasonable
        if modifier_index != total_modifiers:
            mod_string = mod_string + " | "

    return re.sub(search, mod_string, data)


def replace_input_modifier_id_key(
    input_key: str, modifier_number: int, modifier: Modifier, data: str
) -> str:
    """Replaces instances where a particular Modifier key has been used, either with an overall ID, or with specific ID/Value combinations"""
    # Handle INPUT_KEY_MODIFIER_X
    search = re.compile(rf"\b{input_key}_Modifier_{modifier_number}\b", re.IGNORECASE)
    replacement = f"{modifier.modifiers} - {modifier.command}"

    data = re.sub(search, sanitize_string_for_svg(replacement), data)

    # INPUT_KEY_Modifier_1_KEY
    search = re.compile(
        rf"\b{input_key}_Modifier_{modifier_number}_Key\b", re.IGNORECASE
    )
    replacement = f"{modifier.modifiers}"
    data = re.sub(search, sanitize_string_for_svg(replacement), data)

    # INPUT_KEY_Modifier_1_ACTION
    search = re.compile(
        rf"\b{input_key}_Modifier_{modifier_number}_Action\b", re.IGNORECASE
    )
    replacement = f"{modifier.command}"
    data = re.sub(search, sanitize_string_for_svg(replacement), data)

    return data


def replace_input_string(search_key: str, replacement: str, data: str) -> str:
    """Replaces basic keys with their expected action

    BUTTON_X, AXIS_X, POV_X_X
    """
    search = re.compile(rf"\b{search_key}\b", re.IGNORECASE)
    return re.sub(search, sanitize_string_for_svg(replacement), data)


def replace_unused_keys(data: str) -> str:
    """Replaces all unused keys in the template with default values"""
    search_keys = [Template.BUTTON_KEY, Template.AXIS_KEY, Template.HAT_KEY]
    search_keys.extend(Template.MODIFIER_KEYS)

    def find_keys(search_keys: list[re.Pattern]) -> set[str]:
        found_keys = set()
        for key in search_keys:
            result = re.findall(key, data)
            found_keys.update(set(result))
        return found_keys

    aggregated_keys = find_keys(search_keys)

    # Best effort fix to gain performance, word boundaries required to prevent partial replacement depending on ordering of keys
    joined_keys = "|".join({rf"\b{x}\b" for x in aggregated_keys})

    data = re.sub(joined_keys, "", data, flags=re.IGNORECASE)

    return data


def replace_template_date_string(data: str) -> str:
    """Basic replacement of the key with a date at time of run"""
    search = re.compile(rf"\b{TEMPLATE_DATING_KEY}\b", re.IGNORECASE)

    return re.sub(search, datetime.now().strftime("%d/%m/%Y"), data)


def replace_template_name_string(replacement: str, data: str) -> str:
    """Basic replacement of the key with a replacement as name"""
    search = re.compile(rf"\b{TEMPLATE_NAMING_KEY}\b", re.IGNORECASE)
    return re.sub(search, replacement, data)


if __name__ == "__main__":
    replace_unused_keys("button_2")
