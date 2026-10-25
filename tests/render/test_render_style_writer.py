"""Theme writer: per-element writers on fixtures, the hook on fixtures and real templates."""

from datetime import datetime

import pytest
from lxml import etree

from joystick_diagrams.input.button import Button
from joystick_diagrams.render import BindingOptions, RenderContext, render_device
from joystick_diagrams.render.adapters._common import SVG, XHTML, XHTML_NS
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel, MxCell, parse_style
from joystick_diagrams.render.slots import Capability, EdgeRef, ShapeRef
from joystick_diagrams.render.style_writer import (
    css_text_properties,
    font_style_bits,
    format_declarations,
    parse_declarations,
    style_cell_box,
    style_cell_text,
    style_edge,
    style_foreign_div,
    style_shape,
    style_text_element,
)
from joystick_diagrams.render.theme import (
    CLEAN_THEME,
    HIGH_CONTRAST_THEME,
    BoxStyle,
    LineStyle,
    RoleStyle,
    TextStyle,
    Theme,
    ThemeRole,
)
from joystick_diagrams.template import Template
from tests.render.render_fixtures import (
    REPO_ROOT,
    CellSpec,
    DrawioFixture,
    EdgeSpec,
    basic_fixture,
    build_svg,
    export_device_for,
    new_device,
    synthetic_device,
)

NOW = datetime(2026, 1, 2)
TEXT = TextStyle(
    font_family="Noto Sans", font_size=10, font_weight="bold", colour="#112233"
)


def _xhtml(markup: str):
    return etree.fromstring(f'<div xmlns="{XHTML_NS}">{markup}</div>', make_parser())


def _options(**overrides) -> BindingOptions:
    base = {
        "merge_modifiers": False,
        "join_separator": " | ",
        "date_format": "%d/%m/%Y",
        "now": NOW,
    }
    base.update(overrides)
    return BindingOptions(**base)


def _device():
    dev = new_device()
    dev.create_input(Button(1), "Fire")
    dev.add_modifier_to_input(Button(1), {"LShift"}, "Alt Fire")
    return dev


def _render(text, theme=CLEAN_THEME, device=None, **ctx_overrides):
    ed = export_device_for(text, device or _device())
    ctx = RenderContext(theme=theme, now=NOW, **ctx_overrides)
    return render_device(ed, ctx, _options())


def _parse(svg: str):
    return etree.fromstring(svg.encode(), make_parser())


def _innermost_divs(root):
    return [d for d in root.iter(f"{XHTML}div") if d.find(f"{XHTML}div") is None]


# ── CSS declarations ──


def test_declarations_round_trip_in_drawio_spacing():
    decls = parse_declarations(
        "display: inline-block; font-size:12px ;COLOR: rgb(0, 0, 0)"
    )
    assert decls == {
        "display": "inline-block",
        "font-size": "12px",
        "color": "rgb(0, 0, 0)",
    }
    assert (
        format_declarations(decls)
        == "display: inline-block; font-size: 12px; color: rgb(0, 0, 0); "
    )
    assert parse_declarations(None) == {}


def test_css_text_properties_only_for_set_fields():
    assert css_text_properties(TextStyle()) == {}
    assert css_text_properties(TEXT) == {
        "font-family": '"Noto Sans", Arial, sans-serif',
        "font-size": "10px",
        "font-weight": "bold",
        "color": "#112233",
    }


# ── foreignObject ──


def test_style_foreign_div_sets_props_and_strips_nested_font_and_bold():
    outer = _xhtml(
        '<div data-drawio-colors="color: rgb(0, 0, 0); " style="font-size: 0px;">'
        '<div style="display: inline-block; font-size: 12px; color: rgb(0, 0, 0);">'
        '<font style="font-size: 9px; line-height: 1" color="#ff0000" face="Tahoma">'
        "<b>BUTTON_1</b> and <span style='color: blue; font-size: 8px'>x</span></font></div></div>"
    )
    div = _innermost_divs(outer)[0]
    style_foreign_div(div, TEXT)
    decls = parse_declarations(div.get("style"))
    assert decls["font-size"] == "10px" and decls["color"] == "#112233"
    assert decls["display"] == "inline-block"
    font = div.find(f"{XHTML}font")
    assert font.get("color") is None and font.get("face") is None
    assert parse_declarations(font.get("style")) == {"line-height": "1"}
    assert font.find(f"{XHTML}b") is None  # theme decided the weight: <b> unwrapped
    assert "".join(font.itertext()) == "BUTTON_1 and x"
    span = font.find(f"{XHTML}span")
    assert parse_declarations(span.get("style")) == {}
    assert span.get("style") is None
    assert "color: #112233" in div.getparent().get("data-drawio-colors")


def test_style_foreign_div_leaves_unset_properties_alone():
    outer = _xhtml(
        '<div style="display: inline-block; font-size: 12px; color: rgb(0, 0, 0);">'
        '<font style="font-size: 9px"><i>BUTTON_1</i></font></div>'
    )
    div = _innermost_divs(outer)[0]
    style_foreign_div(div, TextStyle(colour="#000000"))
    font = div.find(f"{XHTML}font")
    assert font.get("style") == "font-size: 9px"  # size not set by the theme: kept
    assert font.find(f"{XHTML}i") is not None
    style_foreign_div(div, TextStyle())  # nothing set: nothing changes
    assert font.get("style") == "font-size: 9px"


# ── <text>, shapes, edges ──


def test_style_text_element_writes_attributes():
    text = etree.Element(f"{SVG}text", fill="#000000")
    style_text_element(text, TEXT)
    assert text.get("fill") == "#112233"
    assert text.get("font-weight") == "bold"
    assert text.get("font-size") == "10px"
    assert text.get("font-family").startswith('"Noto Sans"')


def test_style_shape_recolours_but_never_invents_a_box():
    box = BoxStyle(fill="#EEEEEE", stroke="#123456", stroke_width=2, corner_radius=4)
    rect = etree.Element(f"{SVG}rect", fill="#ffffff", stroke="#000000")
    style_shape(ShapeRef(rect), box)
    assert (rect.get("fill"), rect.get("stroke"), rect.get("stroke-width")) == (
        "#EEEEEE",
        "#123456",
        "2",
    )
    assert (rect.get("rx"), rect.get("ry")) == ("4", "4")

    backing = etree.Element(f"{SVG}rect", fill="none", stroke="none")
    style_shape(ShapeRef(backing), box)
    assert backing.attrib == {"fill": "none", "stroke": "none"}

    outline = etree.Element(f"{SVG}rect", fill="none", stroke="#CC0000")
    style_shape(ShapeRef(outline), box)
    assert outline.get("fill") == "none" and outline.get("stroke") == "#123456"

    ellipse = etree.Element(f"{SVG}ellipse", fill="#ffffff", stroke="#000000")
    style_shape(ShapeRef(ellipse), box)
    assert ellipse.get("stroke") == "#123456" and ellipse.get("rx") is None

    group = etree.Element(f"{SVG}g")
    inner = etree.SubElement(group, f"{SVG}path", fill="#ffffff", stroke="#000000")
    style_shape(ShapeRef(group), box)
    assert inner.get("stroke") == "#123456"


def test_style_edge_colours_line_and_arrowheads_and_model():
    g = etree.Element(f"{SVG}g")
    line = etree.SubElement(g, f"{SVG}path", fill="none", stroke="#000000")
    head = etree.SubElement(g, f"{SVG}path", fill="#000000", stroke="#000000")
    cell = MxCell(
        etree.Element("mxCell", style="edgeStyle=orthogonalEdgeStyle;html=1;", edge="1")
    )
    style_edge(
        EdgeRef(cell, g, "a", "b"), LineStyle(stroke="#654321", stroke_width=2.5)
    )
    assert line.get("stroke") == "#654321" and line.get("stroke-width") == "2.5"
    assert head.get("fill") == "#654321" and head.get("stroke") == "#654321"
    assert head.get("stroke-width") is None
    style = parse_style(cell.style)
    assert style["strokeColor"] == "#654321" and style["strokeWidth"] == "2.5"
    assert list(style)[:2] == ["edgeStyle", "html"]  # order kept


# ── Model styles ──


def test_font_style_bits_preserve_underline_and_strikethrough():
    assert font_style_bits("12", TextStyle(font_weight="bold")) == "13"
    assert (
        font_style_bits("15", TextStyle(font_weight="normal", font_style="normal"))
        == "12"
    )
    assert font_style_bits(None, TextStyle(font_style="italic")) == "2"
    assert font_style_bits("garbage", TextStyle(font_weight="bold")) == "1"


def test_style_cell_text_mirrors_theme():
    cell = MxCell(etree.Element("mxCell", style="rounded=1;html=1;fontStyle=4;"))
    style_cell_text(cell, TEXT)
    style = parse_style(cell.style)
    assert style["fontColor"] == "#112233"
    assert style["fontFamily"] == "Noto Sans"  # bare family in the model
    assert style["fontSize"] == "10"
    assert style["fontStyle"] == "5"


def test_style_cell_box_respects_none_fill_and_text_shapes():
    box = BoxStyle(fill="#EEEEEE", stroke="#123456", stroke_width=2, corner_radius=4)
    plain = MxCell(etree.Element("mxCell", style="rounded=0;whiteSpace=wrap;html=1;"))
    style_cell_box(plain, box)
    style = parse_style(plain.style)
    assert style["fillColor"] == "#EEEEEE" and style["strokeColor"] == "#123456"
    assert (style["rounded"], style["absoluteArcSize"], style["arcSize"]) == (
        "1",
        "1",
        "8",
    )

    virpil = MxCell(
        etree.Element(
            "mxCell", style="text;strokeColor=#CC0000;fillColor=none;rounded=1;"
        )
    )
    style_cell_box(virpil, box)
    style = parse_style(virpil.style)
    assert style["strokeColor"] == "#123456" and style["fillColor"] == "none"

    label = MxCell(etree.Element("mxCell", style="text;html=1;align=left;"))
    style_cell_box(label, box)
    assert "strokeColor" not in parse_style(label.style)

    square = MxCell(
        etree.Element("mxCell", style="rounded=1;arcSize=20;absoluteArcSize=1;")
    )
    style_cell_box(square, BoxStyle(corner_radius=0))
    style = parse_style(square.style)
    assert style["rounded"] == "0" and "arcSize" not in style


# ── Hook on fixtures ──


def test_apply_theme_styles_bound_and_unbound_slots_and_model():
    outcome = _render(build_svg(basic_fixture("cellid")), theme=HIGH_CONTRAST_THEME)
    assert Capability.SHAPE_STYLE in outcome.report.capabilities
    root = _parse(outcome.svg_text)
    model = DrawioModel.from_content(root.get("content"))
    cells = model.cells_by_id()
    bound, unbound = parse_style(cells["b1"].style), parse_style(cells["b2"].style)
    assert bound["fontColor"] == "#000000" and bound["strokeWidth"] == "2.5"
    assert unbound["fontColor"] == "#555555" and unbound["fillColor"] == "#EEEEEE"
    assert bound["fontStyle"] == "1" and unbound["fontStyle"] == "0"
    modifier = parse_style(cells["b1m1"].style)
    assert modifier["strokeWidth"] == "2"
    assert parse_style(cells["e1"].style)["strokeColor"] == "#000000"
    assert (
        parse_style(cells["plain"].style).get("fontColor") is None
    )  # no token: untouched

    rects = {(r.get("x"), r.get("y")): r for r in root.iter(f"{SVG}rect")}
    b1_rect = rects[("17.0", "61.0")]  # b1 at model (10, 50) + offset (7, 11)
    assert b1_rect.get("stroke-width") == "2.5" and b1_rect.get("rx") == "0"
    text_fills = {t.get("fill") for t in root.iter(f"{SVG}text")}
    assert {"#000000", "#555555"} <= text_fills
    assert root.get("style").endswith("color-scheme: light;")


def test_apply_theme_is_a_no_op_under_original():
    text = build_svg(basic_fixture("cellid"))
    styled = _render(text, theme=None, engine_override="dom").svg_text
    plain = _render(text, theme=None, engine_override="dom").svg_text
    assert styled == plain
    assert "font-weight" not in styled.split("content=")[0]


def test_text_only_capabilities_get_text_styling_only():
    fx = DrawioFixture(cells=[CellSpec("b1", "BUTTON_1", shape="none")])
    # No labelled vertex geometry match → ordered adapter aligns, but drop the shape
    outcome = _render(build_svg(fx), theme=HIGH_CONTRAST_THEME)
    root = _parse(outcome.svg_text)
    assert all(r.get("stroke-width") is None for r in root.iter(f"{SVG}rect"))
    div = _innermost_divs(root)[0]
    assert parse_declarations(div.get("style"))["font-weight"] == "bold"


def test_leader_line_reaches_rendered_edge_with_cell_ids():
    fx = basic_fixture("cellid")
    fx.edges = [EdgeSpec("e1", "b1", "b1m1")]
    outcome = _render(build_svg(fx), theme=CLEAN_THEME)
    root = _parse(outcome.svg_text)
    edge_paths = [
        p for p in root.iter(f"{SVG}path") if p.get("d", "").startswith("M 50 40")
    ]
    assert edge_paths and edge_paths[0].get("stroke") == "#6B7280"
    assert edge_paths[0].get("stroke-width") == "1.5"


# ── Real templates ──

REAL = [
    REPO_ROOT / "templates" / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg",
    REPO_ROOT / "templates" / "Virpil" / "Virpil Constellation ALPHA R.svg",
    REPO_ROOT / "templates" / "Starter Template.svg",
]
SIZED = Theme(
    theme_id="sized",
    name="sized",
    roles={
        role: RoleStyle(
            text=TextStyle(font_family="Noto Sans", font_size=11, colour="#102030")
        )
        for role in (ThemeRole.BOUND, ThemeRole.UNBOUND, ThemeRole.MODIFIER)
    },
)


@pytest.mark.parametrize("path", REAL, ids=lambda p: p.name)
def test_real_templates_take_a_sized_theme_without_nested_conflicts(path):
    template = Template(str(path))
    device = synthetic_device(template)
    outcome = _render(template.raw_data, theme=SIZED, device=device)
    assert outcome.report.notices == ()
    root = _parse(outcome.svg_text)
    model = DrawioModel.from_content(root.get("content"))
    assert not model.was_compressed

    styled = [
        d
        for d in _innermost_divs(root)
        if parse_declarations(d.get("style")).get("font-size") == "11px"
    ]
    assert styled, "no label received the theme"
    for div in styled:
        for descendant in div.iter():
            if descendant is div or not isinstance(descendant.tag, str):
                continue
            nested = parse_declarations(descendant.get("style"))
            assert "font-size" not in nested and "color" not in nested
            assert descendant.get("color") is None and descendant.get("size") is None
    fonts = {parse_style(c.style).get("fontFamily") for c in model.cells()}
    assert "Noto Sans" in fonts
