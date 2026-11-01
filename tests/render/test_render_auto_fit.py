"""Auto text size: every label takes the largest size that fits its box.

Covers the plain-text fit rules (never shortened, reported at the minimum),
growth up to the ceiling, the three surfaces (foreignObject block, ``<text>``
fallback, model ``fontSize``), the theme model and three dense real templates
measured as written (``make_text_fit_check.measure_written``).
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from lxml import etree

from joystick_diagrams.input.button import Button
from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    ModifierRegistrySnapshot,
)
from joystick_diagrams.render import RenderContext, render_device
from joystick_diagrams.render.adapters._common import SVG, XHTML
from joystick_diagrams.render.binding import BindingOptions, RichText, Run
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel, parse_style
from joystick_diagrams.render.modifier_presentation import (
    full_size_single_line,
    strip_label_font_sizes,
)
from joystick_diagrams.render.slot_fit import (
    DEFAULT_MAX_FONT_SIZE,
    FitPolicy,
    auto_ceiling,
    fit_policy,
    plain_lines,
)
from joystick_diagrams.render.style_writer import parse_declarations
from joystick_diagrams.render.text_fit import (
    DEFAULT_MIN_FONT_SIZE,
    FitBox,
    FontSpec,
    fit_rich,
    line_width,
)
from joystick_diagrams.render.theme import (
    CLEAN_THEME,
    HIGH_CONTRAST_THEME,
    PRINT_FRIENDLY_THEME,
    RoleStyle,
    TextStyle,
    Theme,
    ThemeRole,
)
from tests.render.make_text_fit_check import AUTO_TEMPLATES, render_auto
from tests.render.render_fixtures import (
    CellSpec,
    DrawioFixture,
    build_svg,
    export_device_for,
    new_device,
)

NOW = datetime(2026, 1, 2)
HELVETICA9 = FontSpec("Helvetica", 9.0)


def plain(*texts: str) -> RichText:
    return RichText(tuple((Run(t),) for t in texts))


# ── text_fit: plain text ──


def test_plain_word_longer_than_the_box_stays_whole_at_the_minimum():
    text = plain("Countermeasures_Dispenser_Programme")
    result = fit_rich(text, FitBox(40, 30), HELVETICA9, protected=1, max_size=18)
    assert not result.fits and result.font_size == DEFAULT_MIN_FONT_SIZE
    assert result.lines == text.lines and result.truncated == 0
    assert len(result.wrapped) == 1  # no break inside a word


def test_plain_words_wrap_before_shrinking():
    text = plain("Target Management Switch - Up")
    result = fit_rich(text, FitBox(78, 30), HELVETICA9, protected=1)
    assert result.fits and result.font_size == 9 and len(result.wrapped) >= 2
    for line in result.wrapped:
        assert line_width(line, HELVETICA9) <= 78


def test_plain_text_at_the_minimum_is_never_shortened():
    text = plain(
        "Communications Command Switch - Down / Transmit Secure Voice UHF Radio"
    )
    result = fit_rich(text, FitBox(78, 13), HELVETICA9, protected=1, max_size=18)
    assert not result.fits and result.font_size == DEFAULT_MIN_FONT_SIZE
    assert result.lines == text.lines and result.truncated == 0
    joined = " ".join("".join(r.text for r in line) for line in result.wrapped)
    assert joined == "".join(r.text for r in text.lines[0])  # every word kept


def test_several_plain_lines_are_all_protected():
    text = plain("Roll", "Pitch", "Yaw")
    result = fit_rich(text, FitBox(78, 5), HELVETICA9, protected=3)
    assert not result.fits and result.lines == text.lines


# ── text_fit: growth ──


def test_short_text_in_a_roomy_box_grows_to_the_ceiling():
    result = fit_rich(plain("Fire"), FitBox(78, 30), HELVETICA9, max_size=18)
    assert result.fits and result.font_size == 18 and result.grown
    assert result.line_height == 1.2  # grown text never sits on compact lines


def test_growth_stops_where_the_box_does():
    # 13px tall: one 1.2 line may be at most (13 + 1) / 1.2 = 11.67px.
    result = fit_rich(plain("Fire"), FitBox(78, 13), HELVETICA9, max_size=18)
    assert result.font_size == 11.5 and result.grown
    # 60 × 20px: room for one line only, so the width decides.
    wide = fit_rich(plain("Zoom In Slow"), FitBox(60, 20), HELVETICA9, max_size=18)
    assert wide.grown and len(wide.wrapped) == 1
    assert line_width(wide.wrapped[0], FontSpec("Helvetica", wide.font_size)) <= 60
    assert (
        line_width(wide.wrapped[0], FontSpec("Helvetica", wide.font_size + 0.5)) > 60
        or wide.font_size == 18
    )


def test_without_a_ceiling_the_fit_only_shrinks():
    result = fit_rich(plain("Fire"), FitBox(78, 30), HELVETICA9)
    assert result.font_size == 9 and not result.grown


def test_auto_ceiling_rules():
    policy = fit_policy(TextStyle(fit="auto"))
    assert policy == FitPolicy("auto", DEFAULT_MIN_FONT_SIZE, None, 18.0)
    assert auto_ceiling(policy, 9) == 18  # twice the template size
    assert auto_ceiling(policy, 7) == 14
    assert auto_ceiling(policy, 24) == 24  # never below the template's own size
    assert auto_ceiling(fit_policy(TextStyle(fit="auto", font_size=10)), 9) == 10
    raised = fit_policy(TextStyle(fit="auto", max_font_size=30))
    assert auto_ceiling(raised, 12) == 24
    assert fit_policy(TextStyle(fit="none")) is None
    assert fit_policy(None).mode == "shrink"
    assert DEFAULT_MAX_FONT_SIZE == 18


# ── Theme model ──


def test_theme_json_round_trip_keeps_auto_and_max_size():
    theme = Theme(
        theme_id="mine",
        name="Mine",
        roles={
            ThemeRole.BOUND: RoleStyle(
                text=TextStyle(fit="auto", min_font_size=7, max_font_size=22)
            )
        },
    )
    loaded = Theme.model_validate_json(theme.model_dump_json())
    assert loaded == theme
    text = loaded.text(ThemeRole.BOUND)
    assert (text.fit, text.min_font_size, text.max_font_size) == ("auto", 7, 22)
    # Stored themes from before keep loading.
    old = Theme.model_validate_json(
        '{"theme_id": "o", "name": "O", "roles": {"BOUND": {"text": {"fit": "shrink"}}}}'
    )
    assert old.text(ThemeRole.BOUND).fit == "shrink"


def test_builtins_clean_is_auto_and_the_others_keep_fixed_sizes():
    for role in (ThemeRole.BOUND, ThemeRole.UNBOUND, ThemeRole.MODIFIER):
        assert CLEAN_THEME.text(role).fit == "auto"
    assert CLEAN_THEME.text(ThemeRole.TITLE).fit is None  # titles opt in only
    for theme in (PRINT_FRIENDLY_THEME, HIGH_CONTRAST_THEME):
        assert all(theme.text(role).fit is None for role in ThemeRole)


# ── Reading labels back ──


def test_plain_lines_split_at_breaks_and_blocks_and_collapse_spaces():
    div = etree.fromstring(
        f'<div xmlns="{XHTML[1:-1]}">Roll  <b>left</b><br/>Pitch<div>Yaw</div></div>'
    )
    assert [line[0].text for line in plain_lines(div)] == ["Roll left", "Pitch", "Yaw"]


def test_label_markup_loses_its_own_sizes():
    label = '<font style="font-size: 9px" size="2">Fire</font><span style="color: red; font-size: 8px">x</span>'
    assert (
        strip_label_font_sizes(label)
        == '<font>Fire</font><span style="color: red; ">x</span>'
    )


def test_a_lone_modifier_line_is_written_at_full_size():
    lone = RichText(((Run("Radio menu - ", "#005B8E", size_em=0.85), Run("LShift")),))
    full = full_size_single_line(lone)
    assert all(run.size_em is None for run in full.lines[0])
    two = RichText(((Run("Fire"),), (Run("Alt - LShift", size_em=0.85),)))
    assert full_size_single_line(two) is two


# ── End to end on fixtures ──


def theme_with(**text) -> Theme:
    style = RoleStyle(text=TextStyle(**text))
    return Theme(
        theme_id="t",
        name="t",
        roles={ThemeRole.BOUND: style, ThemeRole.MODIFIER: style},
    )


def render_fixture(command: str, theme: Theme | None, **options):
    """Render one 80 × 13 box (``width``/``height``/``html``/``display``/
    ``modifiers`` change it) bound to ``command``."""
    width = options.get("width", 80)
    height = options.get("height", 13)
    html = options.get("html")
    display = options.get("display", ModifierDisplay.TEMPLATE_BOXES)
    modifiers = options.get("modifiers", ())
    svg = build_svg(
        DrawioFixture(
            cells=[
                CellSpec(
                    "b1",
                    "BUTTON_1",
                    10,
                    50,
                    width,
                    height,
                    style="rounded=0;whiteSpace=wrap;html=1;fontSize=9;",
                    rendered_html=html,
                )
            ],
            edges=[],
            variant="cellid",
        )
    )
    device = new_device()
    device.create_input(Button(1), command)
    for index, mod in enumerate(modifiers):
        device.add_modifier_to_input(Button(1), {f"Key{index}"}, mod)
    ctx = RenderContext(
        theme=theme,
        registry=ModifierRegistrySnapshot.default(),
        modifier_display=display,
        now=NOW,
        engine_override="dom",
    )
    options = BindingOptions(
        merge_modifiers=display is not ModifierDisplay.TEMPLATE_BOXES,
        join_separator=" | ",
        date_format="%d/%m/%Y",
        now=NOW,
        modifier_display=display,
        registry=ctx.registry,
    )
    outcome = render_device(export_device_for(svg, device), ctx, options)
    root = etree.fromstring(outcome.svg_text.encode(), make_parser())
    return outcome, root


def label_div(root, needle: str):
    for div in root.iter(f"{XHTML}div"):
        if "inline-block" in (div.get("style") or "") and needle in "".join(
            div.itertext()
        ):
            return div
    raise AssertionError(f"no label with {needle!r}")


def surfaces(root, needle: str):
    div = label_div(root, needle)
    size = parse_declarations(div.get("style"))["font-size"]
    text = next(t for t in root.iter(f"{SVG}text") if needle in "".join(t.itertext()))
    model = DrawioModel.from_content(root.get("content")).cells_by_id()["b1"]
    return div, size, text, model


def test_auto_shrinks_a_long_plain_label_on_all_three_surfaces():
    outcome, root = render_fixture(
        "Display Management Switch - Down",
        theme_with(fit="auto"),
        html='<font style="font-size: 9px">BUTTON_1</font>',
    )
    div, size, text, model = surfaces(root, "Display")
    assert size.endswith("px") and float(size[:-2]) < 9
    assert div.find(f"{XHTML}font").get("style") is None  # wrapper size moved
    assert "".join(div.itertext()) == "Display Management Switch - Down"
    assert text.get("font-size") == size
    assert len(text.findall(f"{SVG}tspan")) == 2  # wrapped in the fallback too
    assert parse_style(model.style)["fontSize"] == size[:-2]
    assert "font-size" not in model.label
    assert not outcome.report.text_overflow


@pytest.mark.parametrize(
    ("text_style", "expected"),
    [
        ({"fit": "auto"}, "18px"),  # min(2 × 12, 18)
        ({"fit": "auto", "font_size": 14}, "14px"),  # the style's size caps growth
        ({"fit": "auto", "max_font_size": 30}, "24px"),  # a raised cap: 2 × 12
    ],
)
def test_growth_ceiling_on_a_rendered_label(text_style, expected):
    _outcome, root = render_fixture("Fire", theme_with(**text_style), height=60)
    _div, size, text, model = surfaces(root, "Fire")
    assert size == expected
    assert text.get("font-size") == expected
    assert parse_style(model.style)["fontSize"] == expected[:-2]


def test_auto_reports_a_label_too_long_even_at_the_minimum_and_keeps_it_whole():
    command = "Communications Command Switch - Down / Transmit Secure Voice UHF Radio"
    outcome, root = render_fixture(command, theme_with(fit="auto"))
    div, size, _text, _model = surfaces(root, "Communications")
    assert size == "6.5px" and "".join(div.itertext()) == command
    assert outcome.report.text_overflow == (("button_1", command),)
    assert parse_declarations(div.get("style"))["line-height"] == "1"


@pytest.mark.parametrize(
    ("theme", "expected"),
    [
        (None, "12px"),  # Original (unchanged) under the DOM engine
        (theme_with(), "12px"),  # fit unset: "shrink"
        (theme_with(fit="shrink", font_size=10), "10px"),  # a number in the editor
        (theme_with(fit="none"), "12px"),
    ],
    ids=["original", "unset", "fixed_10", "none"],
)
def test_fixed_sizes_and_original_leave_plain_labels_alone(theme, expected):
    outcome, root = render_fixture("Display Management Switch - Down", theme)
    div = label_div(root, "Display")
    assert parse_declarations(div.get("style"))["font-size"] == expected
    assert div.text == "Display Management Switch - Down"  # nothing rewritten
    assert not outcome.report.text_overflow


def test_auto_scales_modifier_lines_with_the_main_line():
    outcome, root = render_fixture(
        "Fire",
        theme_with(fit="auto"),
        height=60,
        display=ModifierDisplay.UNDER_MAIN_TEXT,
        modifiers=("Alt fire",),
    )
    div = label_div(root, "Fire")
    size = float(parse_declarations(div.get("style"))["font-size"][:-2])
    assert size > 12  # grew past the template's 12px
    lines = div.findall(f"{XHTML}div")
    assert [ln.get("style") for ln in lines] == [None, "font-size: 0.85em;"]
    assert not outcome.report.text_overflow


# ── Dense real templates, measured as written ──


@pytest.mark.parametrize("path", AUTO_TEMPLATES, ids=lambda p: p.stem)
@pytest.mark.parametrize(
    ("modifiers", "display"),
    [
        (False, ModifierDisplay.TEMPLATE_BOXES),
        (True, ModifierDisplay.UNDER_MAIN_TEXT),
    ],
    ids=["plain", "under_text"],
)
def test_dense_templates_never_overflow_without_saying_so(path, modifiers, display):
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        outcome, log, check = render_auto(path, modifiers=modifiers, display=display)
    assert check.labels, "no labels measured"
    reported = {key for key, _ in outcome.report.text_overflow}
    for label in check.labels:
        # Every label fits its box as written, or is listed as too long.
        assert not label.overflows or label.key in reported, label
        assert DEFAULT_MIN_FONT_SIZE <= label.font_size <= DEFAULT_MAX_FONT_SIZE
        # The three surfaces agree.
        if label.text_size is not None:
            assert label.text_size == label.font_size, label
        if label.model_size is not None:
            assert label.model_size == label.font_size, label
    # Too long only ever means "too long at the minimum".
    for key, fit in log.fits:
        if key in reported:
            assert fit.font_size == DEFAULT_MIN_FONT_SIZE and not fit.fits
    # Plain text is never shortened.
    if not modifiers:
        assert not outcome.report.overflow
        assert all(fit.truncated == 0 for _, fit in log.fits)
