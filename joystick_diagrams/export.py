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
from joystick_diagrams.app_state import AppState
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.export_text_layout import (
    TextLayoutOptions,
    apply_text_layout_to_token,
    get_text_layout_options,
)
from joystick_diagrams.input.modifier import Modifier
from joystick_diagrams.template import Template

_logger = logging.getLogger(__name__)

TEMPLATE_NAMING_KEY = "TEMPLATE_NAME"
TEMPLATE_DATING_KEY = "CURRENT_DATE"

MERGE_MODIFIERS_SETTING_KEY = "merge_modifiers_into_input"
MODIFIER_JOIN_SEPARATOR = " | "


def merge_modifiers_enabled() -> bool:
    """Whether modifier text is concatenated into the main input key. Default off."""
    from joystick_diagrams.db.db_settings import get_setting

    return get_setting(MERGE_MODIFIERS_SETTING_KEY) == "true"


def _join_input_parts(parts: list[str]) -> str:
    """Joins the parts of an input's text, skipping any empty parts.

    Inputs that only exist because a modifier was bound to them have an empty
    command, so they must not render with a leading separator.
    """
    return MODIFIER_JOIN_SEPARATOR.join(part for part in parts if part)


def export(
    export_device: ExportDevice, output_directory: str, export_format: str = "SVG"
) -> tuple[str, str | None] | None:
    """Export a device. Returns (svg_path, png_path_or_None) on success, None on failure.

    For SVG format: returns (svg_path, None).
    For PNG format: returns (svg_path, png_path) so the caller can queue conversion.
    """
    try:
        return export_device_to_templates(
            export_device, Path(output_directory), export_format
        )
    except PermissionError as e:
        _logger.error(
            f"Permission denied exporting to '{output_directory}': {e}. "
            f"Choose a different export location or check folder permissions."
        )
        raise
    except Exception as e:
        _logger.error(f"Export failed for {export_device}: {e}")
        raise


def export_device_to_templates(
    export_device: ExportDevice, export_location: Path, export_format: str = "SVG"
) -> tuple[str, str | None] | None:
    """Handles the manipulation of the template."""

    if export_device.template is None:
        _logger.error(
            f"There was an issue getting data for the current template: {export_device}"
        )
        return None

    # Replace strings in the template data with device data
    result = populate_template(export_device)

    # TODO handle duplicate file names due to device name clashes
    base_name = f"{export_device.device_id[:5]}-{export_device.device.name}-{export_device.profile_wrapper.profile_name}"

    # Always save SVG first
    svg_file = f"{base_name}.svg"
    save_template(result, svg_file, export_location)
    svg_path = str(export_location / svg_file)

    if export_format == "PNG":
        png_path = str(export_location / f"{base_name}.png")
        return (svg_path, png_path)

    return (svg_path, None)


def save_template(template_data, file_name, export_path):
    utils.create_directory(export_path)

    try:
        with open(export_path.joinpath(file_name), "w", encoding="UTF-8") as f:
            f.write(template_data)
    except PermissionError as err:
        raise PermissionError(
            f"Permission denied writing to '{export_path}'. "
            f"Choose a different export location or check folder permissions."
        ) from err


def _resolve_command(command: str) -> str:
    if AppState._inst is None:
        return command
    return AppState().label_service.resolve(command)


def populate_template(export_device: ExportDevice) -> str:
    """Manipulates template_data to replace known keys with data from Device_"""
    modified_template_data = export_device.template.raw_data
    merge_modifiers = merge_modifiers_enabled()
    text_layout_options = get_text_layout_options()

    for input_key, input_object in export_device.device.get_combined_inputs().items():
        resolved_command = _resolve_command(input_object.command)
        resolved_modifiers = [
            Modifier(m.modifiers, _resolve_command(m.command))
            for m in input_object.modifiers
        ]

        # Optionally fold the modifiers into the main input key, so templates
        # without MODIFIER_X keys still show modifier bindings.
        input_text = resolved_command
        if merge_modifiers and resolved_modifiers:
            input_text = _join_input_parts(
                [resolved_command] + [str(modifier) for modifier in resolved_modifiers]
            )

        modified_template_data = replace_input_string(
            input_key,
            input_text,
            modified_template_data,
            text_layout_options,
        )

        if resolved_modifiers:
            modified_template_data = replace_input_modifiers_string(
                input_key,
                resolved_modifiers,
                modified_template_data,
                text_layout_options,
            )

            for modifier_number, modifier in enumerate(resolved_modifiers, 1):
                modified_template_data = replace_input_modifier_id_key(
                    input_key,
                    modifier_number,
                    modifier,
                    modified_template_data,
                    text_layout_options,
                )

    modified_template_data = replace_template_name_string(
        export_device.profile_wrapper.profile_name, modified_template_data
    )

    modified_template_data = replace_template_date_string(modified_template_data)

    modified_template_data = replace_unused_keys(modified_template_data)

    return modified_template_data


def sanitize_string_for_svg(value_to_sanitize: str) -> str:
    """Safely sanitize a string for inclusion in the SVG template.

    Draw.io SVGs store the mxgraph editor XML inside the root ``<svg>``
    element's ``content="..."`` attribute, so replacement tokens appear inside
    an attribute value delimited by ``"``. A raw ``"`` or ``'`` in the
    replacement would terminate that attribute and produce an invalid SVG
    ("attributes construct error" on load). We therefore escape quotes in
    addition to ``& < >``. The unescape-then-escape pair is idempotent: it
    normalises already-escaped input (``&amp;``/``&quot;``/``&apos;`` etc.) so
    a value that passes through sanitize twice doesn't become ``&amp;quot;``.
    """
    return escape(
        unescape(value_to_sanitize, {"&quot;": '"', "&apos;": "'"}),
        {'"': "&quot;", "'": "&apos;"},
    )


def _replace_dynamic_text_token(
    token: str,
    replacement: str,
    data: str,
    layout_options: TextLayoutOptions | None = None,
) -> str:
    """Apply optional visible-label layout, then perform legacy token replacement."""
    data = apply_text_layout_to_token(data, token, replacement, layout_options)
    search = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
    return re.sub(search, sanitize_string_for_svg(replacement), data)


def replace_input_modifiers_string(
    input_key: str,
    modifiers: list[Modifier],
    data: str,
    layout_options: TextLayoutOptions | None = None,
) -> str:
    """Replaces the INPUT_KEY_MODIFIERS key with combined modifiers from input."""
    token = f"{input_key}_Modifiers"
    mod_string = _join_input_parts([str(modifier) for modifier in modifiers])
    return _replace_dynamic_text_token(token, mod_string, data, layout_options)


def replace_input_modifier_id_key(
    input_key: str,
    modifier_number: int,
    modifier: Modifier,
    data: str,
    layout_options: TextLayoutOptions | None = None,
) -> str:
    """Replace a numbered modifier token and its optional key/action sub-tokens."""
    token = f"{input_key}_Modifier_{modifier_number}"
    data = _replace_dynamic_text_token(token, str(modifier), data, layout_options)

    key_token = f"{token}_Key"
    key_text = "+".join(modifier.modifiers)
    data = _replace_dynamic_text_token(key_token, key_text, data, layout_options)

    action_token = f"{token}_Action"
    return _replace_dynamic_text_token(
        action_token, modifier.command, data, layout_options
    )


def replace_input_string(
    search_key: str,
    replacement: str,
    data: str,
    layout_options: TextLayoutOptions | None = None,
) -> str:
    """Replace a BUTTON, AXIS or POV token with its expected action."""
    return _replace_dynamic_text_token(
        search_key, replacement, data, layout_options
    )


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
    from joystick_diagrams.db.db_settings import get_setting

    search = re.compile(rf"\b{TEMPLATE_DATING_KEY}\b", re.IGNORECASE)
    date_format = get_setting("export_date_format") or "%d/%m/%Y"

    return re.sub(search, datetime.now().strftime(date_format), data)


def replace_template_name_string(replacement: str, data: str) -> str:
    """Basic replacement of the key with a replacement as name"""
    search = re.compile(rf"\b{TEMPLATE_NAMING_KEY}\b", re.IGNORECASE)
    return re.sub(search, replacement, data)


if __name__ == "__main__":
    replace_unused_keys("button_2")
