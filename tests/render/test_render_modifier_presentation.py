"""Modifier presentation: rich runs per display mode, colours, overflow, model labels."""

import dataclasses
from datetime import datetime

from lxml import etree

from joystick_diagrams.export import populate_template
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.modifier import ModifierKind
from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    ModifierKeyDisplay,
    ModifierRegistrySnapshot,
)
from joystick_diagrams.render import BindingOptions, RenderContext, render_device
from joystick_diagrams.render.adapters._common import SVG, XHTML, XHTML_NS
from joystick_diagrams.render.binding import BindingResolver, RichText, Run
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel, parse_style
from joystick_diagrams.render.modifier_presentation import (
    content_host,
    rich_html,
    write_foreign_object,
    write_text_element,
)
from joystick_diagrams.render.theme import CLEAN_THEME
from tests.render.render_fixtures import (
    CellSpec,
    DrawioFixture,
    basic_fixture,
    build_svg,
    export_device_for,
    new_device,
)

NOW = datetime(2026, 1, 2)
COLOURED = ModifierRegistrySnapshot.default(colouring_enabled=True)
SHIFT_TEXT = COLOURED.group(ModifierKind.KEY, "Shift").style.resolved_text_colour
CTRL_TEXT = COLOURED.group(ModifierKind.KEY, "Ctrl").style.resolved_text_colour
ALT_TEXT = COLOURED.group(ModifierKind.KEY, "Alt").style.resolved_text_colour
SHIFT = COLOURED.group(ModifierKind.KEY, "Shift").style.colour


def device():
    dev = new_device()
    dev.create_input(Button(1), "Fire & Forget")
    dev.add_modifier_to_input(Button(1), {"LShift"}, "Alt Fire")
    dev.add_modifier_to_input(Button(1), {"LCtrl", "lalt"}, "Lock <target>")
    dev.add_modifier_to_input(Button(1), {"Long"}, "Eject", kind=ModifierKind.QUALIFIER)
    dev.create_input(Button(2), "Plain")
    return dev


def options(display=ModifierDisplay.TEMPLATE_BOXES, registry=None, **overrides):
    base = {
        "merge_modifiers": display is not ModifierDisplay.TEMPLATE_BOXES,
        "join_separator": " | ",
        "date_format": "%d/%m/%Y",
        "now": NOW,
        "modifier_display": display,
        "registry": registry,
    }
    base.update(overrides)
    return BindingOptions(**base)


def resolver(**kw):
    return BindingResolver(device(), "p", options(**kw))


def render(text, display, registry=None, colour=False, theme=None, **kw):
    ed = export_device_for(text, kw.pop("dev", None) or device())
    ctx = RenderContext(
        theme=theme,
        colour_modifiers=colour,
        registry=registry,
        modifier_display=display,
        now=NOW,
        engine_override="dom",
    )
    return render_device(ed, ctx, options(display, registry, **kw))


def parse(svg):
    return etree.fromstring(svg.encode(), make_parser())


def innermost(root, needle):
    """The label's block (``inline-block`` div); its children are the lines."""
    for div in root.iter(f"{XHTML}div"):
        if "inline-block" in (div.get("style") or "") and needle in "".join(
            div.itertext()
        ):
            return div
    raise AssertionError(f"no label containing {needle!r}")


def text_element(root, needle):
    for text in root.iter(f"{SVG}text"):
        if needle in "".join(text.itertext()):
            return text
    raise AssertionError(f"no <text> containing {needle!r}")


# ── Resolver: rich text mirrors plain text ──


def test_rich_plain_equals_text_for_in_every_mode():
    for display in ModifierDisplay:
        for registry in (None, COLOURED):
            r = resolver(display=display, registry=registry)
            for token in (
                "BUTTON_1",
                "BUTTON_1_MODIFIERS",
                "BUTTON_1_MODIFIER_2",
                "BUTTON_1_MODIFIER_2_KEY",
            ):
                rich = r.rich_for(token)
                assert rich is not None, (display, token)
                assert rich.plain(" | ") == r.text_for(token), (display, token)
            assert r.rich_for("BUTTON_1_MODIFIER_1_ACTION") is None
            assert r.rich_for("BUTTON_9") is None
            assert r.rich_for("TEMPLATE_NAME") is None


def test_under_main_text_lines_and_colours():
    r = resolver(display=ModifierDisplay.UNDER_MAIN_TEXT, registry=COLOURED)
    rich = r.rich_for("BUTTON_1")
    assert [run.text for line in rich.lines for run in line] == [
        "Fire & Forget",
        "Alt Fire - LShift",
        "Lock <target> - LCtrl+lalt",
        "Eject - Long",
    ]
    colours = [line[0].colour for line in rich.lines]
    assert colours == [
        None,
        SHIFT_TEXT,
        CTRL_TEXT,
        None,
    ]  # Ctrl outranks Alt; qualifier uncoloured
    assert all(line[0].size_em for line in rich.lines[1:])
    assert not rich.is_plain


def test_same_line_mode_without_registry_is_plain():
    rich = resolver(display=ModifierDisplay.MERGED_SAME_LINE).rich_for("BUTTON_1")
    assert len(rich.lines) == 1 and rich.is_plain
    assert (
        rich.plain()
        == "Fire & Forget | Alt Fire - LShift | Lock <target> - LCtrl+lalt | Eject - Long"
    )


def test_key_runs_are_coloured_per_key_and_simplified_labels_keep_side():
    r = resolver(registry=COLOURED)
    runs = r.rich_for("BUTTON_1_MODIFIER_2_KEY").lines[0]
    assert [(run.text, run.colour) for run in runs] == [
        ("LCtrl", CTRL_TEXT),
        ("+", None),
        ("lalt", ALT_TEXT),
    ]
    simplified = ModifierRegistrySnapshot.default(
        colouring_enabled=True, key_display=ModifierKeyDisplay.SIMPLIFIED
    )
    r = resolver(registry=simplified)
    assert r.text_for("BUTTON_1_MODIFIER_2_KEY") == "L Ctrl+L Alt"
    assert r.text_for("BUTTON_1_MODIFIER_2") == "Lock <target> - L Ctrl+L Alt"
    assert (
        r.text_for("BUTTON_1_MODIFIER_3_KEY") == "Long"
    )  # qualifiers never relabelled


def test_overflow_hint_only_in_template_boxes_mode_when_opted_in():
    assert (
        resolver(overflow_hint=True).rich_for("BUTTON_2", overflow=2).plain()
        == "Plain +2 more"
    )
    assert resolver().rich_for("BUTTON_2", overflow=2).plain() == "Plain"
    r = resolver(display=ModifierDisplay.UNDER_MAIN_TEXT, overflow_hint=True)
    assert "+2 more" not in r.rich_for("BUTTON_1", overflow=2).plain()


# ── Writers ──


def test_content_host_keeps_font_wrapper_and_writes_lines():
    div = etree.fromstring(
        f'<div xmlns="{XHTML_NS}" style="display: inline-block"><font style="font-size: 9px">BUTTON_1</font></div>',
        make_parser(),
    )
    host = content_host(div)
    assert host.tag == f"{XHTML}font"
    rich = RichText(
        ((Run("Fire"),), (Run("Alt - LShift", colour="#005B8E", size_em=0.85),))
    )
    write_foreign_object(div, rich)
    font = div.find(f"{XHTML}font")
    assert font.get("style") == "font-size: 9px"
    assert font.text is None
    lines = list(font)
    assert [etree.QName(c).localname for c in lines] == ["div", "div"]
    assert lines[0].text == "Fire" and lines[0].get("style") is None
    assert lines[1].get("style") == "font-size: 0.85em;"  # the line's size
    span = lines[1][0]
    assert span.get("style") == "color: #005B8E;"
    assert span.text == "Alt - LShift"

    mixed = etree.fromstring(
        f'<div xmlns="{XHTML_NS}">a<font>b</font>c</div>', make_parser()
    )
    assert content_host(mixed) is mixed  # text outside the wrapper: don't descend


def test_text_element_gets_centred_tspans():
    text = etree.Element(f"{SVG}text", x="100", y="50")
    text.text = "old"
    rich = RichText(((Run("Fire"),), (Run("A", colour="#005B8E"),), (Run("B"),)))
    write_text_element(text, rich)
    lines = list(text)
    assert text.text is None and len(lines) == 3
    assert [t.get("dy") for t in lines] == ["-1.2em", "1.2em", "1.2em"]
    assert all(t.get("x") == "100" for t in lines)
    assert lines[0].text == "Fire"
    inner = lines[1][0]
    assert inner.get("fill") == "#005B8E" and inner.text == "A"


def test_rich_html_escapes_and_wraps():
    rich = RichText(
        ((Run("Fire & <x>"),), (Run("A - B", colour="#005B8E", bold=True),))
    )
    assert (
        rich_html(rich)
        == 'Fire &amp; &lt;x&gt;<br><font color="#005B8E"><b>A - B</b></font>'
    )


# ── End to end ──


def roomy_fixture(variant="cellid"):
    """``basic_fixture`` with a BUTTON_1 box big enough for four 12px lines."""
    fx = basic_fixture(variant)
    fx.cells = [
        dataclasses.replace(c, width=200, height=80) if c.id == "b1" else c
        for c in fx.cells
    ]
    return fx


def test_under_main_text_renders_breaks_tspans_and_model_label():
    outcome = render(
        build_svg(roomy_fixture()),
        ModifierDisplay.UNDER_MAIN_TEXT,
        COLOURED,
        colour=True,
    )
    root = parse(outcome.svg_text)
    div = innermost(root, "Fire & Forget")
    lines = div.findall(f"{XHTML}div")
    assert len(lines) == 4 and lines[0].text == "Fire & Forget"
    assert ["".join(ln.itertext()) for ln in lines[1:]] == [
        "Alt Fire - LShift",
        "Lock <target> - LCtrl+lalt",
        "Eject - Long",
    ]
    assert all(ln.get("style") == "font-size: 0.85em;" for ln in lines[1:])
    assert f"color: {SHIFT_TEXT}" in lines[1][0].get("style")
    assert len(lines[3]) == 0  # qualifier: no colour, so no span at all

    text = text_element(root, "Fire & Forget")
    tspans = text.findall(f"{SVG}tspan")
    assert len(tspans) == 4 and tspans[0].get("dy") == "-1.53em"
    assert tspans[1].get("font-size") == "0.85em" and tspans[1].get("dy") == "1.2em"

    model = DrawioModel.from_content(root.get("content"))
    label = model.cells_by_id()["b1"].label
    assert label.startswith("Fire &amp; Forget<br>")
    assert f'<font color="{SHIFT_TEXT}">' in label and "&lt;target&gt;" in label
    assert parse_style(model.cells_by_id()["b1"].style)["html"] == "1"


def test_modifier_boxes_take_key_colour_when_colouring_is_on():
    text = build_svg(basic_fixture("cellid"))
    root = parse(
        render(text, ModifierDisplay.TEMPLATE_BOXES, COLOURED, colour=True).svg_text
    )
    model = DrawioModel.from_content(root.get("content"))
    cells = model.cells_by_id()
    for cell_id in ("b1m1", "b1m1k", "b1m1a"):
        assert parse_style(cells[cell_id].style)["strokeColor"] == SHIFT, cell_id
    assert "strokeColor" not in parse_style(cells["b1"].style)
    rects = {(r.get("x"), r.get("y")): r for r in root.iter(f"{SVG}rect")}
    assert rects[("17.0", "61.0")].get("stroke") == "#000000"  # b1: model (10, 50)
    assert rects[("107.0", "101.0")].get("stroke") == SHIFT  # b1m1k: model (100, 90)
    key = innermost(root, "LShift")
    assert key.find(f"{XHTML}span").get("style") == f"color: {SHIFT_TEXT};"
    key_model = cells["b1m1k"].label
    assert key_model == f'<font color="{SHIFT_TEXT}">LShift</font>'

    off = parse(render(text, ModifierDisplay.TEMPLATE_BOXES, COLOURED).svg_text)
    off_cells = DrawioModel.from_content(off.get("content")).cells_by_id()
    assert "strokeColor" not in parse_style(off_cells["b1m1"].style)


def test_modifiers_list_box_colours_each_entry():
    root = parse(
        render(
            build_svg(basic_fixture()),
            ModifierDisplay.TEMPLATE_BOXES,
            COLOURED,
            colour=True,
        ).svg_text
    )
    div = innermost(root, "Alt Fire - LShift | ")
    colours = [parse_colour(s.get("style")) for s in div.findall(f"{XHTML}span")]
    assert SHIFT_TEXT in colours and CTRL_TEXT in colours and ALT_TEXT in colours


def parse_colour(style):
    for part in style.split(";"):
        name, _, value = part.partition(":")
        if name.strip() == "color":
            return value.strip()
    return None


def test_overflow_hint_rendered_and_reported_only_with_boxes():
    dev = device()
    one_box = DrawioFixture(
        cells=[CellSpec("b1", "BUTTON_1"), CellSpec("m", "BUTTON_1_MODIFIER_1", y=60)]
    )
    outcome = render(
        build_svg(one_box),
        ModifierDisplay.TEMPLATE_BOXES,
        theme=CLEAN_THEME,
        dev=dev,
        overflow_hint=True,
    )
    assert dict(outcome.report.overflow) == {"BUTTON_1": 2}
    root = parse(outcome.svg_text)
    div = innermost(root, "Fire & Forget")
    assert div.find(f"{XHTML}span").text == " +2 more"
    assert "font-weight: bold" in div.find(f"{XHTML}span").get("style")
    assert (
        "Fire &amp; Forget<b> +2 more</b>"
        in DrawioModel.from_content(root.get("content")).cells_by_id()["b1"].label
    )

    no_boxes = DrawioFixture(cells=[CellSpec("b1", "BUTTON_1")])
    outcome = render(
        build_svg(no_boxes),
        ModifierDisplay.TEMPLATE_BOXES,
        theme=CLEAN_THEME,
        dev=dev,
        overflow_hint=True,
    )
    assert dict(outcome.report.overflow) == {}
    assert "+2 more" not in outcome.svg_text


def test_same_line_mode_matches_legacy_text_without_colours():
    from unittest.mock import patch

    text = build_svg(basic_fixture())
    ed = export_device_for(text, device())
    with patch(
        "joystick_diagrams.db.db_settings.get_setting",
        side_effect={"merge_modifiers_into_input": "true"}.get,
    ):
        legacy = populate_template(ed, now=NOW)
    dom = render(text, ModifierDisplay.MERGED_SAME_LINE).svg_text
    strip = lambda s: " ".join(parse(s).itertext()).split()  # noqa: E731
    assert strip(dom) == strip(legacy)
