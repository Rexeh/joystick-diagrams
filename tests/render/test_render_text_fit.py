"""Text fit (spike S5): measurement, wrapping, shrink/truncate and the three surfaces."""

from datetime import datetime

import pytest
from lxml import etree

from joystick_diagrams.export import _dom_binding_options
from joystick_diagrams.input.button import Button
from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    ModifierRegistrySnapshot,
)
from joystick_diagrams.render import PipelineHooks, RenderContext, render_device
from joystick_diagrams.render.adapters._common import SVG, XHTML
from joystick_diagrams.render.binding import (
    MODIFIER_LINE_SIZE_EM,
    BindingOptions,
    RichText,
    Run,
)
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel, parse_style
from joystick_diagrams.render.modifier_presentation import (
    apply_modifier_presentation,
    css_px,
    foreign_box_width,
    foreign_font,
    write_foreign_object,
    write_text_element,
)
from joystick_diagrams.render.style_writer import (
    apply_theme,
    parse_declarations,
    pin_light_colour_scheme,
)
from joystick_diagrams.render.text_fit import (
    COMPACT_LINE_HEIGHT,
    DEFAULT_MIN_FONT_SIZE,
    LINE_HEIGHT,
    FitBox,
    FontSpec,
    fit_rich,
    line_width,
    text_width,
    wrap_line,
)
from joystick_diagrams.render.theme import (
    CLEAN_THEME,
    RoleStyle,
    TextStyle,
    Theme,
    ThemeRole,
)
from joystick_diagrams.template import Template
from tests.render.make_text_fit_check import FitRecorder, dense_device
from tests.render.render_fixtures import (
    REPO_ROOT,
    CellSpec,
    DrawioFixture,
    build_svg,
    export_device_for,
    new_device,
)

NOW = datetime(2026, 1, 2)
HELVETICA = FontSpec("Helvetica", 10.0)


# ── Measurement ──


def test_width_table_matches_arial_metrics():
    # Liberation Sans / Arial: 'i' is 222, 'W' 944, space 278 per mille (× 1.03 safety).
    assert text_width("i", FontSpec("Arial", 1000.0)) == pytest.approx(222 * 1.03)
    assert text_width("W", HELVETICA) == pytest.approx(9.44 * 1.03)
    assert text_width("a b", HELVETICA) == pytest.approx((556 + 278 + 556) / 100 * 1.03)


def test_bold_narrow_and_unknown_families_scale():
    regular = text_width("Hello", FontSpec("Helvetica", 10))
    assert text_width("Hello", FontSpec("Helvetica", 10, bold=True)) > regular
    assert (
        text_width("Hello", FontSpec('"Liberation Sans Narrow", Arial', 10)) < regular
    )
    assert (
        text_width("Hello", FontSpec("Comic Sans MS", 10)) > regular
    )  # unknown: safe side
    assert text_width("abc", FontSpec("Courier New", 10)) == pytest.approx(3 * 6 * 1.03)
    assert text_width("中", HELVETICA) == pytest.approx(6.0 * 1.03)  # outside the table


def test_run_size_em_scales_width():
    full = line_width((Run("Alt fire"),), HELVETICA)
    small = line_width((Run("Alt fire", size_em=MODIFIER_LINE_SIZE_EM),), HELVETICA)
    assert small == pytest.approx(full * MODIFIER_LINE_SIZE_EM)


# ── Wrapping ──


def test_wrap_breaks_at_spaces_and_keeps_run_attributes():
    line = (
        Run("Jettison stores - ", colour="#112233"),
        Run("lalt+LShift", colour="#445566"),
    )
    wrapped = wrap_line(line, 40.0, FontSpec("Helvetica", 8))
    texts = ["".join(r.text for r in ln) for ln in wrapped]
    assert texts == ["Jettison", "stores -", "lalt+LShift"]
    assert wrapped[2][0].colour == "#445566"
    assert all(not ln[-1].text.endswith(" ") for ln in wrapped)


def test_wrap_leaves_long_words_whole_and_none_width_unwrapped():
    line = (Run("Supercalifragilistic short"),)
    wrapped = wrap_line(line, 20.0, HELVETICA)
    assert ["".join(r.text for r in ln) for ln in wrapped] == [
        "Supercalifragilistic",
        "short",
    ]
    assert wrap_line(line, None, HELVETICA) == [line]


# ── Fitting ──


def rich(*texts: str) -> RichText:
    lines = [(Run(texts[0]),)]
    lines += [(Run(t, size_em=MODIFIER_LINE_SIZE_EM),) for t in texts[1:]]
    return RichText(tuple(lines))


def test_fit_keeps_base_size_when_the_block_fits():
    result = fit_rich(
        rich("Fire", "Alt fire - LShift"), FitBox(78, 30), FontSpec("Helvetica", 8)
    )
    assert result.font_size == 8 and not result.shrunk and not result.compact
    assert result.fits and result.truncated == 0 and len(result.wrapped) == 2


def test_fit_prefers_compact_leading_over_a_smaller_font():
    # 8px main + two 0.85em lines: 25.9px at 1.2 leading, 21.6px at 1.0, so a
    # 24px box takes compact leading at 8px rather than a smaller font.
    result = fit_rich(
        rich("Fire", "a - b", "c - d"), FitBox(78, 24), FontSpec("Helvetica", 8)
    )
    assert result.font_size == 8 and result.line_height == COMPACT_LINE_HEIGHT


def test_fit_shrinks_in_half_pixel_steps_down_to_the_minimum():
    result = fit_rich(
        rich("Weapon release", "Gun arm - LShift"),
        FitBox(78, 13),
        FontSpec("Helvetica", 9),
    )
    # 7.5px + 0.85 × 7.5px compact = 13.9px, within the 1px tolerance of 13px.
    assert result.font_size == 7.5 and result.shrunk and result.fits
    tight = fit_rich(
        rich("Weapon release", "Gun arm - LShift"),
        FitBox(78, 11.1),
        FontSpec("Helvetica", 9),
    )
    assert tight.font_size == DEFAULT_MIN_FONT_SIZE and tight.fits  # 12.03px
    # A word that cannot wrap forces a shrink in half-pixel steps until it fits.
    wide = fit_rich(rich("Countermeasures"), FitBox(60, 30), FontSpec("Helvetica", 9))
    assert 6.5 <= wide.font_size < 9 and wide.font_size * 2 == int(wide.font_size * 2)
    assert line_width(wide.wrapped[0], FontSpec("Helvetica", wide.font_size)) <= 60
    assert line_width(wide.wrapped[0], FontSpec("Helvetica", wide.font_size + 0.5)) > 60


def test_fit_truncates_modifier_lines_and_adds_more_line():
    result = fit_rich(
        rich(
            "Weapon release",
            "Gun arm - LShift",
            "Master arm - RCtrl",
            "Jettison stores - lalt+LShift",
        ),
        FitBox(78, 22),
        FontSpec("Helvetica", 8),
    )
    assert result.fits and result.font_size == DEFAULT_MIN_FONT_SIZE
    # Dropping one line and adding "+1 more" keeps the count, so two go.
    assert result.truncated == 2
    texts = ["".join(r.text for r in ln) for ln in result.lines]
    assert texts == ["Weapon release", "Gun arm - LShift", "+2 more"]
    assert (
        result.lines[-1][0].bold
        and result.lines[-1][0].size_em == MODIFIER_LINE_SIZE_EM
    )


def test_fit_never_drops_the_protected_main_line_and_reports_overflow():
    result = fit_rich(
        rich("Weapon release", "a", "b"), FitBox(78, 6), FontSpec("Helvetica", 8)
    )
    assert not result.fits and result.truncated == 2
    assert "".join(r.text for r in result.lines[0]) == "Weapon release"
    assert "".join(r.text for r in result.lines[1]) == "+2 more"
    single = fit_rich(rich("One line only"), FitBox(10, 4), FontSpec("Helvetica", 8))
    assert (
        not single.fits
        and single.truncated == 0
        and single.lines == rich("One line only").lines
    )


def test_fit_respects_min_size_and_unconstrained_boxes():
    result = fit_rich(
        rich("Fire", "a", "b", "c"),
        FitBox(78, 20),
        FontSpec("Helvetica", 8),
        min_size=7.5,
    )
    assert result.font_size == 7.5 and result.truncated  # never below the floor
    default = fit_rich(
        rich("Fire", "a", "b", "c"), FitBox(78, 20), FontSpec("Helvetica", 8)
    )
    assert default.font_size == DEFAULT_MIN_FONT_SIZE
    free = fit_rich(
        rich("Fire", "a", "b", "c"), FitBox(None, None), FontSpec("Helvetica", 8)
    )
    assert free.fits and not free.shrunk and free.line_height == LINE_HEIGHT


# ── Reading the document ──


def div_from(markup: str):
    return etree.fromstring(
        f'<div xmlns="http://www.w3.org/1999/xhtml">{markup}</div>', make_parser()
    )


def test_css_px_and_foreign_font_from_nested_markup():
    assert (
        css_px("8px") == 8
        and css_px("6pt") == 8
        and css_px("9") == 9
        and css_px("1em") is None
    )
    div = div_from(
        '<div style="display: inline-block; font-size: 12px; font-family: Helvetica;">'
        '<font style="font-size: 9px"><b>BUTTON_11</b></font></div>'
    )[0]
    font = foreign_font(div)
    assert font == FontSpec("Helvetica", 9.0, True)
    sized = div_from(
        '<div style="font-size: 12px;"><font size="2" face="Verdana">x</font></div>'
    )[0]
    assert foreign_font(sized) == FontSpec("Verdana", 13.0, False)


def test_foreign_box_width_reads_the_flex_div():
    outer = div_from(
        '<div style="display: flex; width: 78px; padding-top: 10px;"><div style="font-size: 0px;">'
        '<div style="display: inline-block; font-size: 8px;">x</div></div></div>'
    )[0]
    inner = outer[0][0]
    assert foreign_box_width(inner) == 78.0


def test_visible_frame_clamps_an_invisible_text_cell_to_the_drawn_box():
    from joystick_diagrams.render.modifier_presentation import visible_frame
    from joystick_diagrams.render.slots import Rect

    label = Rect(330, 28, 90, 30)
    frames = [
        Rect(10, 10, 810, 1150),  # page background: too big
        Rect(331, 32, 88, 22),  # the drawn rounded box
        Rect(300, 20, 20, 20),  # the "16" circle next to it
    ]
    assert visible_frame(label, frames) == Rect(331, 32, 88, 22)
    assert visible_frame(Rect(0, 0, 10, 10), frames) is None


def test_render_uses_the_visible_frame_around_an_invisible_text_cell():
    svg = build_svg(
        DrawioFixture(
            cells=[
                CellSpec("frame", "", 11, 54, 78, 22),  # painted box, no token
                CellSpec("b1", "BUTTON_1", 10, 50, 80, 30, shape="none"),
            ],
            edges=[],
            variant="cellid",
        )
    )
    outcome = render(svg)
    root = etree.fromstring(outcome.svg_text.encode(), make_parser())
    div = innermost(root)
    # 4 lines would fit 30px at 6.5px compact (23.1px) but not the 22px frame.
    assert "+2 more" in "".join(div.itertext())


# ── Writing the surfaces ──


def test_write_foreign_object_puts_the_fitted_size_on_the_block():
    div = div_from(
        '<div style="display: inline-block; font-size: 12px; line-height: 1.2;">'
        '<font style="font-size: 9px">BUTTON_1</font></div>'
    )[0]
    fit = fit_rich(
        rich("Weapon release", "Gun arm - LShift"),
        FitBox(78, 11.1),
        FontSpec("Helvetica", 9),
    )
    write_foreign_object(div, RichText(fit.lines), fit)
    declarations = parse_declarations(div.get("style"))
    assert declarations["font-size"] == "6.5px" and declarations["line-height"] == "1"
    font = div.find(f"{XHTML}font")
    assert font is not None and font.get("style") is None  # wrapper size stripped
    lines = font.findall(f"{XHTML}div")
    assert [ln.get("style") for ln in lines] == [None, "font-size: 0.85em;"]
    assert lines[1].text == "Gun arm - LShift"  # the size moved onto the line


def test_write_text_element_wraps_and_sets_size():
    text = etree.Element(f"{SVG}text", x="100", y="20")
    fit = fit_rich(
        rich("Fire", "Countermeasures - JOY_BTN3"),
        FitBox(60, 20),
        FontSpec("Helvetica", 8),
    )
    write_text_element(text, RichText(fit.lines), fit)
    tspans = text.findall(f"{SVG}tspan")
    assert len(tspans) == len(fit.wrapped) >= 3
    assert fit.shrunk and text.get("font-size") == f"{fit.font_size:g}px"
    assert tspans[1].get("dy") == f"{fit.line_height:g}em"


# ── End to end on a fixture ──


def fixture_svg(height: float = 30) -> str:
    return build_svg(
        DrawioFixture(
            cells=[CellSpec("b1", "BUTTON_1", 10, 50, 80, height)],
            edges=[],
            variant="cellid",
        )
    )


def device():
    dev = new_device()
    dev.create_input(Button(1), "Weapon release")
    dev.add_modifier_to_input(Button(1), {"LShift"}, "Gun arm")
    dev.add_modifier_to_input(Button(1), {"RCtrl"}, "Master arm")
    dev.add_modifier_to_input(Button(1), {"lalt", "LShift"}, "Jettison stores")
    return dev


def render(svg: str, theme: Theme | None = None):
    ctx = RenderContext(
        theme=theme,
        colour_modifiers=True,
        registry=ModifierRegistrySnapshot.default(colouring_enabled=True),
        modifier_display=ModifierDisplay.UNDER_MAIN_TEXT,
        now=NOW,
        engine_override="dom",
    )
    options = BindingOptions(
        merge_modifiers=True,
        join_separator=" | ",
        date_format="%d/%m/%Y",
        now=NOW,
        modifier_display=ModifierDisplay.UNDER_MAIN_TEXT,
        registry=ctx.registry,
    )
    return render_device(export_device_for(svg, device()), ctx, options)


def innermost(root):
    """The label's block (the ``inline-block`` div), not its per-line children."""
    for div in root.iter(f"{XHTML}div"):
        if "inline-block" in (div.get("style") or "") and "Weapon" in "".join(
            div.itertext()
        ):
            return div
    raise AssertionError("no label")


def test_render_shrinks_and_truncates_consistently_on_all_surfaces():
    outcome = render(fixture_svg(18))
    root = etree.fromstring(outcome.svg_text.encode(), make_parser())
    div = innermost(root)
    declarations = parse_declarations(div.get("style"))
    assert declarations["font-size"] == "6.5px"
    assert "+2 more" in "".join(div.itertext())
    text = next(t for t in root.iter(f"{SVG}text") if "Weapon" in "".join(t.itertext()))
    assert text.get("font-size") == "6.5px"
    model = DrawioModel.from_content(root.get("content"))
    cell = model.cells_by_id()["b1"]
    assert parse_style(cell.style)["fontSize"] == "6.5"
    assert "+2 more" in cell.label and 'line-height: 1"' in cell.label
    assert outcome.report.overflow == {"BUTTON_1": 2}
    assert any("BUTTON_1" in d and "hidden" in d for d in outcome.report.details)


def test_render_with_room_keeps_every_line_at_the_template_size():
    outcome = render(fixture_svg(90))
    root = etree.fromstring(outcome.svg_text.encode(), make_parser())
    div = innermost(root)
    assert parse_declarations(div.get("style"))["font-size"] == "12px"
    assert "more" not in "".join(div.itertext())
    assert len(div.findall(f"{XHTML}div")) == 4
    assert not outcome.report.overflow


def test_theme_can_turn_fit_off_or_raise_the_minimum():
    off = Theme(
        theme_id="t",
        name="t",
        roles={ThemeRole.BOUND: RoleStyle(text=TextStyle(fit="none"))},
    )
    root = etree.fromstring(
        render(fixture_svg(22), off).svg_text.encode(), make_parser()
    )
    assert "font-size: 12px" in innermost(root).get("style")
    assert "more" not in "".join(innermost(root).itertext())
    floor = Theme(
        theme_id="t",
        name="t",
        roles={ThemeRole.BOUND: RoleStyle(text=TextStyle(min_font_size=8))},
    )
    root = etree.fromstring(
        render(fixture_svg(22), floor).svg_text.encode(), make_parser()
    )
    assert parse_declarations(innermost(root).get("style"))["font-size"] == "8px"


# ── Real templates ──


DENSE = (
    REPO_ROOT / "templates" / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg",
    REPO_ROOT / "templates" / "Virpil" / "Virpil Constellation ALPHA R.svg",
)


@pytest.mark.parametrize("path", DENSE, ids=lambda p: p.stem)
def test_dense_templates_fit_at_least_95_percent_of_slots(path):
    """Every control with three modifiers under the main text (the S5 exit criterion)."""
    template = Template(str(path))
    ed = export_device_for(template.raw_data, dense_device(template), "Dense")
    ctx = RenderContext(
        theme=CLEAN_THEME,
        colour_modifiers=True,
        registry=ModifierRegistrySnapshot.default(colouring_enabled=True),
        modifier_display=ModifierDisplay.UNDER_MAIN_TEXT,
        now=NOW,
        engine_override="dom",
    )
    recorder = FitRecorder()
    hooks = PipelineHooks(
        style=(
            apply_theme,
            recorder,
            apply_modifier_presentation,
            pin_light_colour_scheme,
        )
    )
    outcome = render_device(ed, ctx, _dom_binding_options(ctx), hooks=hooks)
    assert recorder.fits, "no rich slots recorded"
    rate = sum(f.fits for f in recorder.fits) / len(recorder.fits)
    assert rate >= 0.95, rate
    # Every fitted label's written size is between the minimum and the template size.
    for fit in recorder.fits:
        assert DEFAULT_MIN_FONT_SIZE <= fit.font_size <= fit.base_size
    assert "fontSize" in outcome.svg_text
