"""Configurable layout helpers for dynamic text inserted into SVG templates.

Joystick Diagrams templates historically rely on literal token replacement. That is
simple and keeps templates portable, but long action names can overflow the small
label boxes used by many HOTAS templates. This module adds an optional export-time
layout pass for dynamic binding labels while leaving the legacy replacement path
unchanged when the feature is disabled.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, replace

TEXT_LAYOUT_ENABLED_SETTING_KEY = "export_text_layout_enabled"
TEXT_WRAP_ENABLED_SETTING_KEY = "export_text_wrap_enabled"
TEXT_MAX_CHARS_SETTING_KEY = "export_text_max_chars"
TEXT_MAX_LINES_SETTING_KEY = "export_text_max_lines"
TEXT_FONT_SIZE_SETTING_KEY = "export_text_font_size"
TEXT_SHRINK_ENABLED_SETTING_KEY = "export_text_shrink_enabled"
TEXT_MIN_FONT_SIZE_SETTING_KEY = "export_text_min_font_size"
TEXT_ELLIPSIS_SETTING_KEY = "export_text_ellipsis_enabled"

DEFAULT_TEXT_LAYOUT_ENABLED = False
DEFAULT_TEXT_WRAP_ENABLED = True
DEFAULT_TEXT_MAX_CHARS = 18
DEFAULT_TEXT_MAX_LINES = 3
DEFAULT_TEXT_FONT_SIZE = 0  # 0 = preserve template font size
DEFAULT_TEXT_SHRINK_ENABLED = True
DEFAULT_TEXT_MIN_FONT_SIZE = 7
DEFAULT_TEXT_ELLIPSIS_ENABLED = False
DEFAULT_TEMPLATE_FONT_SIZE = 12.0
LINE_HEIGHT_EM = 1.1

_TEXT_ELEMENT_RE = re.compile(
    r"(?P<open><text\b[^>]*>)(?P<body>.*?)(?P<close></text>)",
    flags=re.IGNORECASE | re.DOTALL,
)
_HTML_TEXT_ELEMENT_RE = re.compile(
    r"(?P<open><(?P<tag>div|span|p)\b[^>]*>)(?P<body>[^<>]*)(?P<close></(?P=tag)>)",
    flags=re.IGNORECASE | re.DOTALL,
)
_TSPAN_RE = re.compile(
    r"<tspan\b(?P<attrs>[^>]*)>.*?</tspan>",
    flags=re.IGNORECASE | re.DOTALL,
)
_XML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class TextLayoutOptions:
    """Export-time rules used to fit dynamic binding labels into templates."""

    enabled: bool = DEFAULT_TEXT_LAYOUT_ENABLED
    wrap: bool = DEFAULT_TEXT_WRAP_ENABLED
    max_chars: int = DEFAULT_TEXT_MAX_CHARS
    max_lines: int = DEFAULT_TEXT_MAX_LINES
    font_size: int = DEFAULT_TEXT_FONT_SIZE
    shrink: bool = DEFAULT_TEXT_SHRINK_ENABLED
    min_font_size: int = DEFAULT_TEXT_MIN_FONT_SIZE
    ellipsis: bool = DEFAULT_TEXT_ELLIPSIS_ENABLED


def _read_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value == "true"


def _read_int(
    value: str | None,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    return min(maximum, max(minimum, parsed))


def get_text_layout_options() -> TextLayoutOptions:
    """Read text layout settings once for an export operation."""
    from joystick_diagrams.db.db_settings import get_setting

    return TextLayoutOptions(
        enabled=_read_bool(
            get_setting(TEXT_LAYOUT_ENABLED_SETTING_KEY), DEFAULT_TEXT_LAYOUT_ENABLED
        ),
        wrap=_read_bool(
            get_setting(TEXT_WRAP_ENABLED_SETTING_KEY), DEFAULT_TEXT_WRAP_ENABLED
        ),
        max_chars=_read_int(
            get_setting(TEXT_MAX_CHARS_SETTING_KEY),
            DEFAULT_TEXT_MAX_CHARS,
            4,
            120,
        ),
        max_lines=_read_int(
            get_setting(TEXT_MAX_LINES_SETTING_KEY),
            DEFAULT_TEXT_MAX_LINES,
            1,
            8,
        ),
        font_size=_read_int(
            get_setting(TEXT_FONT_SIZE_SETTING_KEY),
            DEFAULT_TEXT_FONT_SIZE,
            0,
            48,
        ),
        shrink=_read_bool(
            get_setting(TEXT_SHRINK_ENABLED_SETTING_KEY),
            DEFAULT_TEXT_SHRINK_ENABLED,
        ),
        min_font_size=_read_int(
            get_setting(TEXT_MIN_FONT_SIZE_SETTING_KEY),
            DEFAULT_TEXT_MIN_FONT_SIZE,
            5,
            48,
        ),
        ellipsis=_read_bool(
            get_setting(TEXT_ELLIPSIS_SETTING_KEY), DEFAULT_TEXT_ELLIPSIS_ENABLED
        ),
    )


def _get_attribute(tag: str, name: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        tag,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(2) if match else None


def _set_attribute(tag: str, name: str, value: str) -> str:
    pattern = re.compile(
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        flags=re.IGNORECASE | re.DOTALL,
    )
    if pattern.search(tag):
        return pattern.sub(f'{name}="{value}"', tag, count=1)
    return tag[:-1] + f' {name}="{value}">'


def _get_fragment_attribute(attributes: str, name: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        attributes,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(2) if match else None


def _set_fragment_attribute(attributes: str, name: str, value: str) -> str:
    pattern = re.compile(
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        flags=re.IGNORECASE | re.DOTALL,
    )
    if pattern.search(attributes):
        return pattern.sub(f'{name}="{value}"', attributes, count=1)
    return attributes + f' {name}="{value}"'


def _remove_fragment_attribute(attributes: str, name: str) -> str:
    return re.sub(
        rf"\s*\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        "",
        attributes,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _get_style_property(tag: str, property_name: str) -> str | None:
    style = _get_attribute(tag, "style")
    if not style:
        return None

    match = re.search(
        rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*([^;]+)",
        style,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _set_style_property(tag: str, property_name: str, value: str) -> str:
    style = _get_attribute(tag, "style") or ""
    pattern = re.compile(
        rf"((?:^|;)\s*{re.escape(property_name)}\s*:)\s*[^;]+",
        flags=re.IGNORECASE,
    )

    if pattern.search(style):
        style = pattern.sub(rf"\1 {value}", style, count=1)
    else:
        if style and not style.rstrip().endswith(";"):
            style += ";"
        style += f" {property_name}: {value};"

    return _set_attribute(tag, "style", style.strip())


def _parse_numeric_font_size(value: str | None) -> float | None:
    if not value:
        return None

    match = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def _template_font_size(open_tag: str) -> float | None:
    direct = _parse_numeric_font_size(_get_attribute(open_tag, "font-size"))
    if direct is not None:
        return direct
    return _parse_numeric_font_size(_get_style_property(open_tag, "font-size"))


def _set_font_size(open_tag: str, font_size: float) -> str:
    rendered = f"{font_size:g}"
    if _get_attribute(open_tag, "font-size") is not None:
        return _set_attribute(open_tag, "font-size", rendered)
    if _get_style_property(open_tag, "font-size") is not None:
        return _set_style_property(open_tag, "font-size", f"{rendered}px")
    return _set_attribute(open_tag, "font-size", rendered)


def _attribute_bool(open_tag: str, name: str, default: bool) -> bool:
    value = _get_attribute(open_tag, name)
    if value is None:
        return default
    return value.casefold() in {"1", "true", "yes", "on"}


def _attribute_int(
    open_tag: str,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    return _read_int(_get_attribute(open_tag, name), default, minimum, maximum)


def _node_options(open_tag: str, options: TextLayoutOptions) -> TextLayoutOptions:
    """Apply optional per-text SVG overrides on top of the global settings."""
    if _get_attribute(open_tag, "data-jd-layout") == "off":
        return replace(options, enabled=False)

    return replace(
        options,
        wrap=_attribute_bool(open_tag, "data-jd-wrap", options.wrap),
        max_chars=_attribute_int(
            open_tag, "data-jd-max-chars", options.max_chars, 4, 120
        ),
        max_lines=_attribute_int(
            open_tag, "data-jd-max-lines", options.max_lines, 1, 8
        ),
        font_size=_attribute_int(
            open_tag, "data-jd-font-size", options.font_size, 0, 48
        ),
        shrink=_attribute_bool(open_tag, "data-jd-shrink", options.shrink),
        min_font_size=_attribute_int(
            open_tag,
            "data-jd-min-font-size",
            options.min_font_size,
            5,
            48,
        ),
        ellipsis=_attribute_bool(open_tag, "data-jd-ellipsis", options.ellipsis),
    )


def _wrap_words(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def _wrap_paragraph(text: str, max_chars: int) -> list[str]:
    """Wrap a paragraph, preferring action separators as line boundaries."""
    action_parts = [part.strip() for part in text.split("|")]
    if len(action_parts) == 1:
        return _wrap_words(text, max_chars)

    lines: list[str] = []
    for action_part in action_parts:
        part_lines = _wrap_words(action_part, max_chars)
        for index, part_line in enumerate(part_lines):
            separator = " | " if index == 0 and lines else " "
            candidate = f"{lines[-1]}{separator}{part_line}" if lines else part_line
            if lines and len(candidate) <= max_chars:
                lines[-1] = candidate
            else:
                lines.append(part_line)

    return lines


def wrap_label(text: str, max_chars: int) -> list[str]:
    """Greedily wrap a label while respecting explicit newlines and ``|`` actions."""
    normalized_lines = [" ".join(line.split()) for line in text.splitlines()]
    if not normalized_lines:
        return [""]

    result: list[str] = []
    for line in normalized_lines:
        result.extend(_wrap_paragraph(line, max_chars))
    return result or [""]


def _truncate_line(line: str, max_chars: int) -> str:
    if len(line) <= max_chars:
        return line
    if max_chars <= 1:
        return "…"
    return line[: max_chars - 1].rstrip() + "…"


def _apply_ellipsis(lines: list[str], max_lines: int, max_chars: int) -> list[str]:
    visible = [_truncate_line(line, max_chars) for line in lines[:max_lines]]
    if len(lines) <= max_lines:
        return visible

    hidden_text = " ".join(lines[max_lines:]).strip()
    if hidden_text:
        visible[-1] = _truncate_line(f"{visible[-1]} …", max_chars)
        if not visible[-1].endswith("…"):
            visible[-1] = _truncate_line(f"{visible[-1]}…", max_chars)
    return visible


def fit_label(
    text: str,
    options: TextLayoutOptions,
    template_font_size: float | None = None,
) -> tuple[list[str], float]:
    """Return wrapped lines and the selected font size for a label.

    ``max_chars`` represents the approximate capacity at the starting font size.
    When shrinking is enabled, smaller font sizes proportionally increase the
    effective character capacity. This keeps the implementation independent from
    a specific Qt/font renderer and therefore works for both SVG and HTML labels.
    """
    normalized = " ".join(text.split()) if "\n" not in text else text.strip()
    original_font_size = template_font_size or DEFAULT_TEMPLATE_FONT_SIZE
    start_font_size = float(options.font_size or original_font_size)
    min_font_size = min(start_font_size, float(options.min_font_size))

    candidate_font_size = start_font_size
    selected_lines = [normalized]
    selected_capacity = options.max_chars

    while True:
        scale = start_font_size / candidate_font_size if candidate_font_size else 1.0
        effective_capacity = max(1, round(options.max_chars * scale))
        lines = (
            wrap_label(normalized, effective_capacity)
            if options.wrap
            else [normalized]
        )

        fits_width = all(len(line) <= effective_capacity for line in lines)
        fits = (
            len(lines) <= options.max_lines and fits_width
            if options.wrap
            else len(normalized) <= effective_capacity
        )
        selected_lines = lines
        selected_capacity = effective_capacity
        if fits or not options.shrink or candidate_font_size <= min_font_size:
            break

        candidate_font_size = max(min_font_size, candidate_font_size - 1.0)

    if options.ellipsis:
        selected_lines = _apply_ellipsis(
            selected_lines, options.max_lines, selected_capacity
        )

    return selected_lines, candidate_font_size


def _visible_text(body: str) -> str:
    return html.unescape(_XML_TAG_RE.sub("", body)).strip()


def _escape_line(line: str) -> str:
    from joystick_diagrams.export import sanitize_string_for_svg

    return sanitize_string_for_svg(line)


def _build_svg_text_body(
    body: str,
    open_tag: str,
    lines: list[str],
) -> str:
    if len(lines) == 1:
        token_text = _visible_text(body)
        if not token_text:
            return _escape_line(lines[0])
        token_pattern = re.compile(re.escape(token_text), flags=re.IGNORECASE)
        return token_pattern.sub(_escape_line(lines[0]), body, count=1)

    tspan_match = _TSPAN_RE.search(body)
    if tspan_match:
        attributes = tspan_match.group("attrs")
    else:
        text_x = _get_attribute(open_tag, "x") or "0"
        attributes = f' x="{text_x}"'

    x_value = (
        _get_fragment_attribute(attributes, "x")
        or _get_attribute(open_tag, "x")
        or "0"
    )
    first_attributes = _remove_fragment_attribute(attributes, "dy")
    first_offset = -((len(lines) - 1) * LINE_HEIGHT_EM / 2)
    first_attributes = _set_fragment_attribute(
        first_attributes, "dy", f"{first_offset:g}em"
    )

    following_attributes = _remove_fragment_attribute(attributes, "y")
    following_attributes = _remove_fragment_attribute(following_attributes, "dy")
    following_attributes = _set_fragment_attribute(following_attributes, "x", x_value)

    rendered = [f"<tspan{first_attributes}>{_escape_line(lines[0])}</tspan>"]
    rendered.extend(
        f'<tspan{_set_fragment_attribute(following_attributes, "dy", f"{LINE_HEIGHT_EM:g}em")}>{_escape_line(line)}</tspan>'
        for line in lines[1:]
    )
    return "".join(rendered)


def _layout_svg_text_elements(
    data: str,
    token: str,
    replacement_text: str,
    options: TextLayoutOptions,
) -> str:
    token_folded = token.casefold()

    def replace_text_element(match: re.Match[str]) -> str:
        body = match.group("body")
        if _visible_text(body).casefold() != token_folded:
            return match.group(0)

        open_tag = match.group("open")
        node_options = _node_options(open_tag, options)
        if not node_options.enabled:
            return match.group(0)

        original_font_size = _template_font_size(open_tag)
        lines, selected_font_size = fit_label(
            replacement_text,
            node_options,
            original_font_size,
        )

        baseline_font_size = original_font_size or DEFAULT_TEMPLATE_FONT_SIZE
        if node_options.font_size or selected_font_size < baseline_font_size:
            open_tag = _set_font_size(open_tag, selected_font_size)

        new_body = _build_svg_text_body(body, open_tag, lines)
        return f"{open_tag}{new_body}{match.group('close')}"

    return _TEXT_ELEMENT_RE.sub(replace_text_element, data)


def _layout_html_text_elements(
    data: str,
    token: str,
    replacement_text: str,
    options: TextLayoutOptions,
) -> str:
    token_folded = token.casefold()

    def replace_html_element(match: re.Match[str]) -> str:
        body = html.unescape(match.group("body")).strip()
        if body.casefold() != token_folded:
            return match.group(0)

        open_tag = match.group("open")
        node_options = _node_options(open_tag, options)
        if not node_options.enabled:
            return match.group(0)

        original_font_size = _template_font_size(open_tag)
        lines, selected_font_size = fit_label(
            replacement_text,
            node_options,
            original_font_size,
        )

        baseline_font_size = original_font_size or DEFAULT_TEMPLATE_FONT_SIZE
        if node_options.font_size or selected_font_size < baseline_font_size:
            open_tag = _set_font_size(open_tag, selected_font_size)
        if len(lines) > 1:
            open_tag = _set_style_property(
                open_tag, "line-height", f"{LINE_HEIGHT_EM:g}"
            )

        new_body = "<br/>".join(_escape_line(line) for line in lines)
        return f"{open_tag}{new_body}{match.group('close')}"

    return _HTML_TEXT_ELEMENT_RE.sub(replace_html_element, data)


def apply_text_layout_to_token(
    data: str,
    token: str,
    replacement_text: str,
    options: TextLayoutOptions | None,
) -> str:
    """Layout visible instances of ``token`` before the normal global replacement.

    The function intentionally only rewrites text/HTML nodes whose *entire visible
    content* is the token. Other occurrences (including draw.io's embedded editor
    metadata) are left for the existing plain token replacement, preserving template
    editability and backwards compatibility.
    """
    if options is None or not options.enabled:
        return data

    result = _layout_svg_text_elements(data, token, replacement_text, options)
    return _layout_html_text_elements(result, token, replacement_text, options)
