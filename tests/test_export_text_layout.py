import xml.etree.ElementTree as ET
from unittest.mock import patch

from joystick_diagrams.export import replace_input_string
from joystick_diagrams.export_text_layout import (
    DEFAULT_TEXT_ELLIPSIS_ENABLED,
    DEFAULT_TEXT_FONT_SIZE,
    DEFAULT_TEXT_LAYOUT_ENABLED,
    DEFAULT_TEXT_MAX_CHARS,
    DEFAULT_TEXT_MAX_LINES,
    DEFAULT_TEXT_MIN_FONT_SIZE,
    DEFAULT_TEXT_SHRINK_ENABLED,
    DEFAULT_TEXT_WRAP_ENABLED,
    TEXT_ELLIPSIS_SETTING_KEY,
    TEXT_FONT_SIZE_SETTING_KEY,
    TEXT_LAYOUT_ENABLED_SETTING_KEY,
    TEXT_MAX_CHARS_SETTING_KEY,
    TEXT_MAX_LINES_SETTING_KEY,
    TEXT_MIN_FONT_SIZE_SETTING_KEY,
    TEXT_SHRINK_ENABLED_SETTING_KEY,
    TEXT_WRAP_ENABLED_SETTING_KEY,
    TextLayoutOptions,
    fit_label,
    get_text_layout_options,
    wrap_label,
)


def _simple_svg(token: str = "BUTTON_5") -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<text transform="matrix(1 0 0 1 100 100)" x="0" y="0" '
        'font-family="Helvetica" font-size="12" text-anchor="middle">'
        f'<tspan x="0" y="0">{token}</tspan>'
        "</text></svg>"
    )


def test_defaults_preserve_legacy_export_behavior():
    svg = _simple_svg()
    result = replace_input_string("BUTTON_5", "A very long binding name", svg)

    assert "A very long binding name" in result
    assert "<br/>" not in result
    assert result.count("<tspan") == 1
    assert 'font-size="12"' in result


def test_wrap_label_prefers_action_separators():
    lines = wrap_label(
        "Smoke Toggle | Spray Toggle | Toggle Afterburner",
        max_chars=18,
    )

    assert lines == ["Smoke Toggle", "Spray Toggle", "Toggle Afterburner"]


def test_fit_label_shrinks_until_target_line_count_is_reached():
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=12,
        max_lines=2,
        font_size=12,
        shrink=True,
        min_font_size=6,
    )

    lines, font_size = fit_label(
        "Firefighting Scoop Doors Grapple Hook Toggle",
        options,
        template_font_size=12,
    )

    assert len(lines) <= 2
    assert font_size < 12
    assert font_size >= 6


def test_svg_text_is_wrapped_and_font_is_reduced():
    svg = _simple_svg()
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=18,
        max_lines=3,
        font_size=11,
        shrink=True,
        min_font_size=8,
    )

    result = replace_input_string(
        "BUTTON_5",
        "Smoke Toggle | Spray Toggle | Toggle Afterburner",
        svg,
        options,
    )

    assert "BUTTON_5" not in result
    assert result.count("<tspan") == 3
    assert "Smoke Toggle" in result
    assert "Spray Toggle" in result
    assert "Toggle Afterburner" in result
    assert 'font-size="11"' in result
    ET.fromstring(result)


def test_multiline_svg_text_stays_centered_around_original_baseline():
    svg = _simple_svg()
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=10,
        max_lines=3,
        shrink=False,
    )

    result = replace_input_string(
        "BUTTON_5",
        "Engine Auto Shutdown",
        svg,
        options,
    )

    assert 'dy="-1.1em"' in result
    assert result.count('dy="1.1em"') == 2
    ET.fromstring(result)


def test_special_characters_remain_valid_xml_after_layout():
    svg = _simple_svg()
    options = TextLayoutOptions(enabled=True, max_chars=10, max_lines=3)

    result = replace_input_string(
        "BUTTON_5",
        'Master "A&B" <Toggle>',
        svg,
        options,
    )

    assert "&quot;" in result
    assert "&amp;" in result
    assert "&lt;" in result
    ET.fromstring(result)


def test_plain_drawio_metadata_still_uses_normal_token_replacement():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" content="BUTTON_5">'
        '<text x="0" y="0" font-size="12"><tspan>BUTTON_5</tspan></text>'
        "</svg>"
    )
    options = TextLayoutOptions(enabled=True, max_chars=8, max_lines=3)

    result = replace_input_string(
        "BUTTON_5",
        "Engine Auto Shutdown",
        svg,
        options,
    )

    assert 'content="Engine Auto Shutdown"' in result
    assert result.count("Engine Auto Shutdown") == 1
    assert result.count("<tspan") > 1
    ET.fromstring(result)


def test_simple_foreign_object_html_label_uses_line_breaks():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml" '
        'style="font-size: 12px;">BUTTON_5</div></foreignObject>'
        "</svg>"
    )
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=10,
        max_lines=3,
        font_size=10,
    )

    result = replace_input_string(
        "BUTTON_5",
        "Engine Auto Shutdown",
        svg,
        options,
    )

    assert "<br/>" in result
    assert "font-size: 10px" in result
    ET.fromstring(result)


def test_per_text_svg_overrides_global_layout_settings():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<text x="0" y="0" font-size="12" data-jd-max-chars="8" '
        'data-jd-max-lines="2" data-jd-font-size="9">'
        "<tspan>BUTTON_5</tspan></text></svg>"
    )
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=30,
        max_lines=1,
        font_size=12,
        shrink=False,
    )

    result = replace_input_string(
        "BUTTON_5",
        "Engine Auto Shutdown",
        svg,
        options,
    )

    assert result.count("<tspan") >= 2
    assert 'font-size="9"' in result
    ET.fromstring(result)


def test_per_text_layout_can_be_disabled():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<text x="0" y="0" font-size="12" data-jd-layout="off">'
        "<tspan>BUTTON_5</tspan></text></svg>"
    )
    options = TextLayoutOptions(enabled=True, max_chars=5, max_lines=2)

    result = replace_input_string(
        "BUTTON_5",
        "Engine Auto Shutdown",
        svg,
        options,
    )

    assert result.count("<tspan") == 1
    assert "Engine Auto Shutdown" in result
    ET.fromstring(result)


def test_ellipsis_is_opt_in_and_enforces_max_lines():
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=8,
        max_lines=2,
        font_size=10,
        shrink=False,
        ellipsis=True,
    )

    lines, _ = fit_label(
        "one two three four five six seven eight",
        options,
        template_font_size=10,
    )

    assert len(lines) == 2
    assert lines[-1].endswith("…")


def test_settings_reader_uses_defaults_when_values_are_missing():
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        options = get_text_layout_options()

    assert options == TextLayoutOptions(
        enabled=DEFAULT_TEXT_LAYOUT_ENABLED,
        wrap=DEFAULT_TEXT_WRAP_ENABLED,
        max_chars=DEFAULT_TEXT_MAX_CHARS,
        max_lines=DEFAULT_TEXT_MAX_LINES,
        font_size=DEFAULT_TEXT_FONT_SIZE,
        shrink=DEFAULT_TEXT_SHRINK_ENABLED,
        min_font_size=DEFAULT_TEXT_MIN_FONT_SIZE,
        ellipsis=DEFAULT_TEXT_ELLIPSIS_ENABLED,
    )


def test_settings_reader_parses_and_clamps_stored_values():
    stored = {
        TEXT_LAYOUT_ENABLED_SETTING_KEY: "true",
        TEXT_WRAP_ENABLED_SETTING_KEY: "false",
        TEXT_MAX_CHARS_SETTING_KEY: "999",
        TEXT_MAX_LINES_SETTING_KEY: "0",
        TEXT_FONT_SIZE_SETTING_KEY: "11",
        TEXT_SHRINK_ENABLED_SETTING_KEY: "true",
        TEXT_MIN_FONT_SIZE_SETTING_KEY: "7",
        TEXT_ELLIPSIS_SETTING_KEY: "true",
    }

    with patch(
        "joystick_diagrams.db.db_settings.get_setting",
        side_effect=stored.get,
    ):
        options = get_text_layout_options()

    assert options.enabled is True
    assert options.wrap is False
    assert options.max_chars == 120
    assert options.max_lines == 1
    assert options.font_size == 11
    assert options.shrink is True
    assert options.min_font_size == 7
    assert options.ellipsis is True
