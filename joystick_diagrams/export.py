"""Handles the creation of Exported items from Joystick Diagrams.

Supplied <DeviceMapping> and list[Profile]

Author: Robert Cox
"""

import logging
import re
from dataclasses import dataclass
from dataclasses import replace as dataclass_replace
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape, unescape

from joystick_diagrams import utils
from joystick_diagrams.app_state import AppState
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.input.modifier import Modifier
from joystick_diagrams.modifier_identity import (
    LEGACY_MERGE_MODIFIERS_SETTING_KEY,
    ModifierDisplay,
    get_modifier_display,
    modifiers_in_main_text,
)
from joystick_diagrams.render import (
    BindingOptions,
    Engine,
    RenderContext,
    RenderFallbackError,
    RenderNotice,
    RenderOutcome,
    RenderReport,
    build_render_context,
    choose_engine,
    render_device,
)
from joystick_diagrams.template import Template

_logger = logging.getLogger(__name__)

TEMPLATE_NAMING_KEY = "TEMPLATE_NAME"
TEMPLATE_DATING_KEY = "CURRENT_DATE"

# Kept for downgrade safety and the legacy tests; the user-facing choice is
# ``modifier_identity.get_modifier_display()`` ("Showing modifiers").
MERGE_MODIFIERS_SETTING_KEY = LEGACY_MERGE_MODIFIERS_SETTING_KEY
MODIFIER_JOIN_SEPARATOR = " | "

EXPORT_DATE_FORMAT_SETTING_KEY = "export_date_format"
DEFAULT_EXPORT_DATE_FORMAT = "%d/%m/%Y"


def merge_modifiers_enabled() -> bool:
    """Whether modifier text is folded into the main input key. Default off.

    Reads through ``get_modifier_display()``: ``MERGED_SAME_LINE`` (and the
    migrated legacy ``merge_modifiers_into_input == "true"``) keep today's
    ``" | "`` join byte for byte; ``UNDER_MAIN_TEXT`` also counts, so a DOM
    render that falls back to this engine still shows every modifier.
    """
    return modifiers_in_main_text(get_modifier_display())


def export_date_format() -> str:
    """The strftime format for CURRENT_DATE, read at call time."""
    from joystick_diagrams.db.db_settings import get_setting

    return get_setting(EXPORT_DATE_FORMAT_SETTING_KEY) or DEFAULT_EXPORT_DATE_FORMAT


def _join_input_parts(parts: list[str]) -> str:
    """Joins the parts of an input's text, skipping any empty parts.

    Inputs that only exist because a modifier was bound to them have an empty
    command, so they must not render with a leading separator.
    """
    return MODIFIER_JOIN_SEPARATOR.join(part for part in parts if part)


@dataclass(frozen=True)
class ExportOutput:
    """What one export produced: the SVG path, the PNG path to convert to (or
    ``None``) and the render report (``None`` when the template was missing)."""

    svg_path: str
    png_path: str | None
    report: RenderReport | None

    @property
    def paths(self) -> tuple[str, str | None]:
        return (self.svg_path, self.png_path)


def export(
    export_device: ExportDevice,
    output_directory: str,
    export_format: str = "SVG",
    ctx: RenderContext | None = None,
) -> tuple[str, str | None] | None:
    """Export a device. Returns (svg_path, png_path_or_None) on success, None on failure.

    For SVG format: returns (svg_path, None).
    For PNG format: returns (svg_path, png_path) so the caller can queue conversion.

    ``ctx`` is the per-batch RenderContext snapshot; callers should build it once
    on the UI thread. When omitted one is built here so the hidden
    ``render_engine`` setting still works end-to-end.
    """
    output = export_with_report(export_device, output_directory, export_format, ctx)
    return output.paths if output is not None else None


def export_with_report(
    export_device: ExportDevice,
    output_directory: str,
    export_format: str = "SVG",
    ctx: RenderContext | None = None,
) -> ExportOutput | None:
    """``export`` plus the ``RenderReport`` (for the export summary dialog)."""
    try:
        return _export_device(
            export_device,
            Path(output_directory),
            export_format,
            ctx if ctx is not None else build_render_context(),
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
    export_device: ExportDevice,
    export_location: Path,
    export_format: str = "SVG",
    ctx: RenderContext | None = None,
) -> tuple[str, str | None] | None:
    """Handles the manipulation of the template."""
    output = _export_device(export_device, export_location, export_format, ctx)
    return output.paths if output is not None else None


def _export_device(
    export_device: ExportDevice,
    export_location: Path,
    export_format: str = "SVG",
    ctx: RenderContext | None = None,
) -> ExportOutput | None:
    if export_device.template is None:
        _logger.error(
            f"There was an issue getting data for the current template: {export_device}"
        )
        return None

    # Replace strings in the template data with device data
    outcome = render_template(export_device, ctx)
    result = outcome.svg_text

    # TODO handle duplicate file names due to device name clashes
    base_name = f"{export_device.device_id[:5]}-{export_device.device.name}-{export_device.profile_wrapper.profile_name}"

    # Always save SVG first
    svg_file = f"{base_name}.svg"
    save_template(result, svg_file, export_location)
    svg_path = str(export_location / svg_file)

    if export_format == "PNG":
        png_path = str(export_location / f"{base_name}.png")
        return ExportOutput(svg_path, png_path, outcome.report)

    return ExportOutput(svg_path, None, outcome.report)


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


# ── Engine selection ──


def _template_label(export_device: ExportDevice) -> str:
    template = getattr(export_device, "template", None)
    return str(
        getattr(template, "template_key", None)
        or getattr(template, "template_file_name", None)
        or template
    )


def _legacy_outcome(
    export_device: ExportDevice,
    ctx: RenderContext | None,
    notices: tuple[RenderNotice, ...] = (),
    details: tuple[str, ...] = (),
) -> RenderOutcome:
    now = ctx.now if ctx is not None else None
    report = RenderReport(engine=Engine.LEGACY, notices=notices, details=details)
    return RenderOutcome(populate_template(export_device, now=now), report)


def dom_binding_options(ctx: RenderContext) -> BindingOptions:
    """The ``BindingOptions`` the DOM engine (and the layout editor) derive from a context."""
    display = ModifierDisplay(ctx.modifier_display)
    return BindingOptions(
        merge_modifiers=modifiers_in_main_text(display),
        join_separator=MODIFIER_JOIN_SEPARATOR,
        date_format=export_date_format(),
        labels=ctx.labels,
        now=ctx.now,
        modifier_display=display,
        registry=ctx.registry,
        # The hint only appears once the user opted into styling, so the hidden
        # ``render_engine=dom`` flag under Original stays text-identical to legacy.
        overflow_hint=ctx.theme is not None or ctx.colour_modifiers,
    )


_dom_binding_options = dom_binding_options  # name used by earlier tests


def render_template(
    export_device: ExportDevice, ctx: RenderContext | None
) -> RenderOutcome:
    """Render with the chosen engine. ``ctx is None`` is exactly ``populate_template``.

    The DOM engine falls back to the legacy engine on any ``RenderFallbackError``
    (parse error, not draw.io, coverage mismatch) or unexpected exception; the
    template and reason are logged at WARNING and recorded in the report.
    """
    if ctx is None or choose_engine(ctx, export_device) is Engine.LEGACY:
        return _legacy_outcome(export_device, ctx)

    try:
        return render_device(export_device, ctx, dom_binding_options(ctx))
    except RenderFallbackError as e:
        _logger.warning(
            f"DOM render of {_template_label(export_device)} fell back to legacy: "
            f"{e.notice.value} ({e.detail})"
        )
        notices = (e.notice, RenderNotice.FELL_BACK_TO_LEGACY)
        return _legacy_outcome(export_device, ctx, notices, (e.detail,))
    except Exception as e:
        _logger.warning(
            f"DOM render of {_template_label(export_device)} failed unexpectedly, "
            f"falling back to legacy: {e}",
            exc_info=True,
        )
        notices = (RenderNotice.UNEXPECTED_ERROR, RenderNotice.FELL_BACK_TO_LEGACY)
        return _legacy_outcome(export_device, ctx, notices, (str(e),))


# ── Legacy regex engine ──


def populate_template(export_device: ExportDevice, now: datetime | None = None) -> str:
    """Manipulates template_data to replace known keys with data from Device_"""
    modified_template_data = export_device.template.raw_data
    merge_modifiers = merge_modifiers_enabled()

    for input_key, input_object in export_device.device.get_combined_inputs().items():
        resolved_command = _resolve_command(input_object.command)
        resolved_modifiers = [
            dataclass_replace(m, command=_resolve_command(m.command))
            for m in input_object.modifiers
        ]

        # Optionally fold the modifiers into the main input key, so templates
        # without MODIFIER_X keys still show modifier bindings
        input_text = resolved_command
        if merge_modifiers and resolved_modifiers:
            input_text = _join_input_parts(
                [sanitize_string_for_svg(resolved_command)]
                + [sanitize_string_for_svg(str(mod)) for mod in resolved_modifiers]
            )

        modified_template_data = replace_input_string(
            input_key,
            input_text,
            modified_template_data,
        )

        if resolved_modifiers:
            modified_template_data = replace_input_modifiers_string(
                input_key, resolved_modifiers, modified_template_data
            )

            for modifier_number, modifier in enumerate(resolved_modifiers, 1):
                modified_template_data = replace_input_modifier_id_key(
                    input_key, modifier_number, modifier, modified_template_data
                )

    modified_template_data = replace_template_name_string(
        export_device.profile_wrapper.profile_name, modified_template_data
    )

    modified_template_data = replace_template_date_string(modified_template_data, now)

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


def replace_input_modifiers_string(
    input_key: str, modifiers: list[Modifier], data: str
) -> str:
    """Replaces the INPUT_KEY_MODIFIERS key with combined modifiers from input"""
    search = re.compile(rf"\b{input_key}_Modifiers\b", re.IGNORECASE)

    # Create Modifier Strings
    # Due to way SVG handles new lines, this is a compromise for modifiers to be joined and look reasonable
    mod_string = _join_input_parts(
        [sanitize_string_for_svg(str(modifier)) for modifier in modifiers]
    )

    return re.sub(search, mod_string, data)


def replace_input_modifier_id_key(
    input_key: str, modifier_number: int, modifier: Modifier, data: str
) -> str:
    """Replaces instances where a particular Modifier key has been used, either with an overall ID, or with specific ID/Value combinations"""
    # Handle INPUT_KEY_MODIFIER_X
    search = re.compile(rf"\b{input_key}_Modifier_{modifier_number}\b", re.IGNORECASE)
    replacement = str(modifier)

    data = re.sub(search, sanitize_string_for_svg(replacement), data)

    # INPUT_KEY_Modifier_1_KEY
    search = re.compile(
        rf"\b{input_key}_Modifier_{modifier_number}_Key\b", re.IGNORECASE
    )
    replacement = "+".join(modifier.sorted_keys)
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


def replace_template_date_string(data: str, now: datetime | None = None) -> str:
    """Basic replacement of the key with a date at time of run (or ``now`` when given)"""
    search = re.compile(rf"\b{TEMPLATE_DATING_KEY}\b", re.IGNORECASE)
    date_format = export_date_format()

    return re.sub(search, (now or datetime.now()).strftime(date_format), data)


def replace_template_name_string(replacement: str, data: str) -> str:
    """Basic replacement of the key with a replacement as name"""
    search = re.compile(rf"\b{TEMPLATE_NAMING_KEY}\b", re.IGNORECASE)
    return re.sub(search, replacement, data)


if __name__ == "__main__":
    replace_unused_keys("button_2")
