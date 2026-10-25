"""Parity suite: legacy regex engine vs DOM engine over the whole template corpus.

For every bundled template (plus tests/data/template_test.svg) a synthetic
device binds a deterministic subset of the discovered tokens (single-key
modifiers, token-free command text, frozen date). Both engines render and the
visible text per text node must be identical. Known divergences are explicit.
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from lxml import etree

from joystick_diagrams.export import (
    MERGE_MODIFIERS_SETTING_KEY,
    populate_template,
    render_template,
)
from joystick_diagrams.render import (
    RENDER_ENGINE_SETTING_KEY,
    Engine,
    build_render_context,
)
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.tokens import BLANK_RE, find_tokens
from joystick_diagrams.template import Template
from tests.render.render_fixtures import CORPUS, export_device_for, synthetic_device

NOW = datetime(2026, 1, 2)

# file name -> why the two engines legitimately differ
KNOWN_DIVERGENCES: dict[str, set[str]] = {
    # Legacy never touches a compressed model; DOM decodes, fills and writes it
    # back uncompressed. Rendered text is identical, model labels are not compared.
    "Thrustmaster Warthog - Joystick.svg": {"compressed_model"},
    "Thrustmaster Warthog - Throttle.svg": {"compressed_model"},
    "VKB-Sim Gladiator NXT L.svg": {"compressed_model"},
    "VKB-Sim Gladiator NXT R.svg": {"compressed_model"},
    "Virpil Control Panel #1.svg": {"compressed_model"},
    "Virpil Stick VFX.svg": {"compressed_model"},
    "Virpil Stick WarBRD.svg": {"compressed_model"},
    "Virpil Throttle MT-50 CM2.svg": {"compressed_model"},
}
# Divergence classes that apply to inputs, not files (covered in test_render_fill):
#   - commands containing `& " <`: legacy corrupts the inner model (bug 1)
#   - backslashes: legacy re.sub reinterprets them (bug 3)
#   - TEMPLATE_NAME with `& " <`: legacy writes invalid XML (bug 4)
#   - commands containing a token ("Same as BUTTON_2"): legacy chains (bug 5)
#   - AXIS_SLIDER_10 and other multi-digit axes: DOM blanks/fills, legacy shows (bug 6)


def _parse(svg: str):
    return etree.fromstring(svg.encode("utf-8"), make_parser())


def _text_sequence(root) -> list[tuple[str, str | None, str | None]]:
    tree = root.getroottree()
    out = []
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        text = node.text if node.text and node.text.strip() else None
        tail = node.tail if node.tail and node.tail.strip() else None
        if text is not None or tail is not None:
            out.append((tree.getpath(node), text, tail))
    return out


def _settings(merge: bool):
    values = {RENDER_ENGINE_SETTING_KEY: "dom"}
    if merge:
        values[MERGE_MODIFIERS_SETTING_KEY] = "true"
    return patch(
        "joystick_diagrams.db.db_settings.get_setting",
        side_effect=values.get,
    )


def _render_both(path, merge: bool):
    template = Template(str(path))
    device = synthetic_device(template)
    ed = export_device_for(template.raw_data, device, "Profile X")
    with _settings(merge):
        legacy = populate_template(ed, now=NOW)
        outcome = render_template(ed, build_render_context(now=NOW))
    assert outcome.report.engine is Engine.DOM, outcome.report
    return template, legacy, outcome


def _check_parity(path, merge: bool, tmp_path) -> None:
    template, legacy, outcome = _render_both(path, merge)
    legacy_root = _parse(legacy)
    dom_root = _parse(outcome.svg_text)
    assert _text_sequence(legacy_root) == _text_sequence(dom_root)
    assert outcome.report.notices == ()
    _assert_dimensions_still_parse(legacy, outcome.svg_text, tmp_path)

    # invariants on the DOM output
    pristine_model = DrawioModel.from_content(_parse(template.raw_data).get("content"))
    model = DrawioModel.from_content(dom_root.get("content"))
    assert not model.was_compressed
    assert len(model.cells()) == len(pristine_model.cells())
    for cell in model.cells():
        assert not BLANK_RE.search(cell.plain_label), (cell.id, cell.label)
    _assert_model_labels_match_text(pristine_model, model, outcome, dom_root)

    if "compressed_model" not in KNOWN_DIVERGENCES.get(path.name, set()):
        legacy_model = DrawioModel.from_content(legacy_root.get("content"))
        assert [c.plain_label for c in legacy_model.cells()] == [
            c.plain_label for c in model.cells()
        ]


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.name)
def test_visible_text_parity(path, tmp_path):
    """Modifier boxes mode (default), every template."""
    _check_parity(path, False, tmp_path)


# One file per structural variant, plus a compressed model and the test template.
MERGED_SUBSET = [
    p
    for p in CORPUS
    if p.name
    in {
        "Starter Template.svg",
        "Virpil Constellation ALPHA L.svg",
        "URSA MINOR Fighter Joystick R - Axis POV.svg",
        "VKB-Sim Gladiator NXT L.svg",
        "template_test.svg",
    }
]


@pytest.mark.parametrize("path", MERGED_SUBSET, ids=lambda p: p.name)
def test_visible_text_parity_merged_modifiers(path, tmp_path):
    """Merged-modifiers mode on a representative subset (legacy is slow on big files)."""
    _check_parity(path, True, tmp_path)


def _assert_dimensions_still_parse(legacy: str, dom: str, tmp_path) -> None:
    from joystick_diagrams.export_image import parse_svg_dimensions

    out = tmp_path / "out.svg"
    out.write_text(dom, encoding="utf-8")
    ref = tmp_path / "ref.svg"
    ref.write_text(legacy, encoding="utf-8")
    assert parse_svg_dimensions(out) == parse_svg_dimensions(ref)
    assert parse_svg_dimensions(out) != (800, 600)


def _assert_model_labels_match_text(pristine, model, outcome, dom_root):
    """Every single-token model label ends up as the text the body shows for it."""
    body_texts = {
        " ".join(t.split())
        for el in dom_root.iter()
        if isinstance(el.tag, str) and el.text
        for t in [el.text]
    }
    filled = {cell.id: cell for cell in model.cells()}
    for cell in pristine.cells():
        tokens = find_tokens(cell.plain_label)
        if len(tokens) != 1 or cell.plain_label.lower() != tokens[0]:
            continue
        label = " ".join(filled[cell.id].plain_label.split())
        assert label == "" or label in body_texts, (cell.id, label)
