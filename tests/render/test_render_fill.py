"""Token fill semantics: BindingResolver + single-pass fill, and the DOM output invariants."""

from datetime import datetime

import pytest
from lxml import etree

from joystick_diagrams.input.button import Button
from joystick_diagrams.render import BindingOptions, RenderContext, render_device
from joystick_diagrams.render.binding import BindingResolver, fill_text
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.tokens import BLANK_RE
from tests.render.render_fixtures import (
    CellSpec,
    DrawioFixture,
    basic_fixture,
    build_svg,
    export_device_for,
    new_device,
)

NOW = datetime(2026, 1, 2, 3, 4, 5)


def options(**overrides) -> BindingOptions:
    base = {
        "merge_modifiers": False,
        "join_separator": " | ",
        "date_format": "%d/%m/%Y",
        "labels": None,
        "now": NOW,
    }
    base.update(overrides)
    return BindingOptions(**base)


def resolver(device, profile="profile_1", **overrides) -> BindingResolver:
    return BindingResolver(device, profile, options(**overrides))


def device_with_modifiers():
    dev = new_device()
    dev.create_input(Button(1), "Fire")
    dev.add_modifier_to_input(Button(1), {"LShift"}, "Alt Fire")
    dev.add_modifier_to_input(Button(1), {"LCtrl"}, "Lock")
    dev.create_input(Button(2), "Same as BUTTON_1")
    return dev


# ── resolver semantics ──


def test_action_modifier_and_blank_tokens():
    r = resolver(device_with_modifiers())
    assert r.text_for("BUTTON_1") == "Fire"
    assert r.text_for("button_1") == "Fire"  # case-insensitive
    assert r.text_for("BUTTON_1_MODIFIERS") == "Alt Fire - LShift | Lock - LCtrl"
    assert r.text_for("BUTTON_1_MODIFIER_1") == "Alt Fire - LShift"
    assert r.text_for("BUTTON_1_Modifier_2_Key") == "LCtrl"
    assert r.text_for("BUTTON_1_MODIFIER_2_ACTION") == "Lock"
    assert r.text_for("BUTTON_1_MODIFIER_3") == ""  # out of range → blanked
    assert r.text_for("BUTTON_2_MODIFIERS") == ""  # no modifiers → blanked
    assert r.text_for("BUTTON_9") == ""  # unbound
    assert r.text_for("POV_1_LL") == ""  # legacy-only shape
    assert r.text_for("BUTTON_1_MODIFIER_1_STYLE") == ""
    assert r.text_for("TEMPLATE_NAME") == "profile_1"
    assert r.text_for("CURRENT_DATE") == "02/01/2026"


def test_merged_modifiers_and_empty_parts():
    dev = device_with_modifiers()
    dev.add_modifier_to_input(
        Button(9), {"ctrl"}, "Shell Mod"
    )  # shell input, command ""
    r = resolver(dev, merge_modifiers=True)
    assert r.text_for("BUTTON_1") == "Fire | Alt Fire - LShift | Lock - LCtrl"
    assert r.text_for("BUTTON_9") == "Shell Mod - ctrl"
    assert r.text_for("BUTTON_2") == "Same as BUTTON_1"


def test_labels_snapshot_applies_to_commands_and_modifier_commands():
    r = resolver(device_with_modifiers(), labels={"Fire": "FIRE!", "Lock": "Target"})
    assert r.text_for("BUTTON_1") == "FIRE!"
    assert r.text_for("BUTTON_1_MODIFIER_2") == "Target - LCtrl"
    assert r.text_for("BUTTON_1_MODIFIER_2_ACTION") == "Target"


def test_unescape_normalisation_matches_legacy():
    dev = new_device()
    dev.create_input(Button(1), "a &amp; b")
    dev.create_input(Button(2), "it&apos;s &quot;q&quot; &lt;x&gt;")
    dev.create_input(Button(3), 'raw & " < > \\n \\0')
    r = resolver(dev)
    assert r.text_for("BUTTON_1") == "a & b"
    assert r.text_for("BUTTON_2") == 'it\'s "q" <x>'
    assert r.text_for("BUTTON_3") == 'raw & " < > \\n \\0'


def test_html_for_escapes_markup_but_not_quotes():
    dev = new_device()
    dev.create_input(Button(1), 'a & "b" <c>')
    assert resolver(dev).html_for("BUTTON_1") == 'a &amp; "b" &lt;c&gt;'


def test_template_name_with_specials_is_plain_text():
    r = resolver(new_device(), profile='Rob & "Co" <1>')
    assert r.text_for("TEMPLATE_NAME") == 'Rob & "Co" <1>'


# ── single pass fill ──


def test_fill_text_is_single_pass_and_literal():
    dev = device_with_modifiers()
    r = resolver(dev)
    out = fill_text("BUTTON_2 / BUTTON_1 / BUTTON_7", r.text_for)
    assert out == "Same as BUTTON_1 / Fire / "  # replacement never rescanned


def test_fill_text_multi_token_and_case_variants():
    dev = device_with_modifiers()
    r = resolver(dev)
    assert fill_text("Button_1 BUTTON_1_modifier_1_KEY", r.text_for) == "Fire LShift"


def test_backslashes_are_literal():
    dev = new_device()
    dev.create_input(Button(1), r"C:\new\table \0 \b")
    assert fill_text("BUTTON_1", resolver(dev).text_for) == r"C:\new\table \0 \b"


# ── end to end on a fixture ──


def _render(fx: DrawioFixture, dev, profile="profile_1", **opts):
    ed = export_device_for(build_svg(fx), dev, profile)
    return render_device(
        ed, RenderContext(engine_override="dom", now=NOW), options(**opts)
    )


def _parse(svg: str):
    return etree.fromstring(svg.encode("utf-8"), make_parser())


def _texts(root) -> list[str]:
    """Every non-blank text node (element text and tails) under ``root``."""
    out: list[str] = []
    for el in root.iter():
        if isinstance(el.tag, str) and el.text and el.text.strip():
            out.append(el.text)
        if el.tail and el.tail.strip():
            out.append(el.tail)
    return out


def test_render_fills_body_and_model_and_blanks_unused():
    outcome = _render(basic_fixture(), device_with_modifiers(), profile='P & "Q"')
    root = _parse(outcome.svg_text)
    texts = _texts(root)
    assert texts.count("Fire") == 2  # foreignObject div + <text>
    assert "Alt Fire - LShift | Lock - LCtrl" in texts
    assert "LShift" in texts and "Alt Fire" in texts
    assert 'P & "Q"' in texts
    assert "02/01/2026" in texts
    assert "Same as BUTTON_1" in texts  # not chained
    assert not any(BLANK_RE.search(t) for t in texts if t != "Same as BUTTON_1")
    model = DrawioModel.from_content(root.get("content"))
    labels = {cell.id: cell.label for cell in model.cells()}
    assert labels["b1"] == "Fire"
    assert labels["t"] == 'P &amp; "Q"'  # html=1 label: markup-escaped once
    assert labels["odd"] == ""  # POV_1_LL blanked in the model too
    assert labels["ax"] == ""  # unbound axis blanked
    assert labels["plain"] == "Just a label"
    assert outcome.report.overflow == {"BUTTON_1": 1}  # 2 modifiers, 1 box


@pytest.mark.parametrize("compressed", [False, True])
def test_specials_produce_valid_svg_and_model(compressed):
    dev = new_device()
    dev.create_input(Button(1), 'Fire &amp; "Forget" <now> \\ \\n')
    fx = basic_fixture(compressed=compressed)
    fx.cells[2].style = "whiteSpace=wrap;html=0;"  # plain-text model value
    outcome = _render(fx, dev)
    root = _parse(outcome.svg_text)
    assert 'Fire & "Forget" <now> \\ \\n' in _texts(root)
    model = DrawioModel.from_content(root.get("content"))
    assert not model.was_compressed
    assert model.cells_by_id()["b1"].label == 'Fire & "Forget" <now> \\ \\n'
    assert model.cells_by_id()["b1m1"].label == ""


def test_multi_placeholder_br_cell():
    dev = new_device()
    dev.create_input(Button(62), "Sixty two")
    dev.create_input(Button(35), "Thirty five")
    fx = DrawioFixture(
        cells=[
            CellSpec(
                "m", "BUTTON_62<br>BUTTON_35", rendered_html="BUTTON_62<br/>BUTTON_35"
            )
        ]
    )
    outcome = _render(fx, dev)
    root = _parse(outcome.svg_text)
    assert "Thirty five" in _texts(root)  # tail after <br/> filled
    model = DrawioModel.from_content(root.get("content"))
    assert model.cells_by_id()["m"].label == "Sixty two<br>Thirty five"


def test_wrapper_label_and_tooltip_filled():
    dev = new_device()
    dev.create_input(Button(1), "Fire")
    fx = DrawioFixture(
        cells=[CellSpec("u", "BUTTON_1", wrapper="UserObject", tooltip="BUTTON_1 tip")]
    )
    outcome = _render(fx, dev)
    model = DrawioModel.from_content(_parse(outcome.svg_text).get("content"))
    cell = model.cells_by_id()["u"]
    assert cell.label == "Fire"
    assert cell.tooltip == "Fire tip"


def test_pre_escaped_amp_displays_as_single_ampersand():
    dev = new_device()
    dev.create_input(Button(1), "a &amp; b")
    outcome = _render(basic_fixture(), dev)
    root = _parse(outcome.svg_text)
    # body text node: escaped exactly once by lxml, decodes to a single ampersand
    assert ">a &amp; b<" in outcome.svg_text
    assert "a & b" in _texts(root)
    # html=1 model label: HTML-escaped once (draw.io shows "a & b"); the extra
    # levels in the raw file are the model XML attribute and the SVG content
    # attribute, both added and removed by the XML parsers.
    model = DrawioModel.from_content(root.get("content"))
    assert model.cells_by_id()["b1"].label == "a &amp; b"
    assert model.cells_by_id()["b1"].plain_label == "a & b"
