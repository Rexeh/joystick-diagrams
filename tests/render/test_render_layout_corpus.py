"""Layout stage on real bundled templates: edge mapping, rotated cells, duplicates, editor render."""

from datetime import datetime
from pathlib import Path

import pytest
from lxml import etree

from joystick_diagrams.render.adapters import detect_adapter
from joystick_diagrams.render.adapters.edge_mapping import path_endpoints, stroke_paths
from joystick_diagrams.render.document import TemplateDocument, make_parser
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.editor import EditorOptions, render_for_editor
from joystick_diagrams.render.layout import (
    AddModifierBoxesOp,
    HideOp,
    LayoutDocument,
    LayoutLayers,
    MoveOp,
    ResizeOp,
)
from joystick_diagrams.render.layout_scene import build_scene
from joystick_diagrams.template import Template
from tests.render.render_fixtures import CORPUS, REPO_ROOT

NOW = datetime(2026, 1, 2)
SVG = "{http://www.w3.org/2000/svg}"
TEMPLATES = REPO_ROOT / "templates"
APACHE = TEMPLATES / "Total Controls" / "Total Controls - Apache MPD.svg"
VIRPIL = TEMPLATES / "Virpil" / "Virpil Constellation ALPHA R.svg"
ORION = (
    TEMPLATES / "WinWing" / "Orion2 18 Joystick Combo" / "Orion2 18 Joystick Combo.svg"
)
CONTROL_PANEL = TEMPLATES / "Virpil" / "Virpil Control Panel #1.svg"
# Model edges draw.io does not draw (self-loops or a terminal point inside the source cell).
UNRENDERED_EDGES = {
    "T.16000M Joystick Right Handed.svg": 1,
    "Total Controls - Multi Function Button Box.svg": 1,
    "T1-SUPER TARUS THROTTLE.svg": 1,
    "URSA MINOR Fighter Joystick L - Axis POV.svg": 1,
    "URSA MINOR Fighter Joystick L - Button POV.svg": 1,
    "URSA MINOR Fighter Joystick R - Axis POV.svg": 1,
    "URSA MINOR Fighter Joystick R - Button POV.svg": 1,
}


def slot_map_for(path: Path):
    doc = TemplateDocument.parse(path.read_text(encoding="utf-8"))
    model = DrawioModel.from_content(doc.root.get("content"))
    return detect_adapter(doc, model).build_slots(doc, model), doc, model


@pytest.mark.parametrize(
    "path",
    [p for p in CORPUS if p.parent != REPO_ROOT / "tests" / "data"],
    ids=lambda p: p.name,
)
def test_every_rendered_edge_is_mapped(path):
    slot_map, doc, _model = slot_map_for(path)
    rendered = len(stroke_paths(doc.root))
    paths = [p for p in (e.stroke_path for e in slot_map.edges) if p is not None]
    assert len(paths) == rendered
    assert len(slot_map.edges) - len(paths) == UNRENDERED_EDGES.get(path.name, 0)
    assert len({id(p) for p in paths}) == len(paths)  # no two edges share a line


def test_apache_rotated_cells_keep_shapes_and_refuse_resize():
    slot_map, doc, model = slot_map_for(APACHE)
    rotated = [s for s in slot_map.slots if s.rotated]
    assert len(rotated) == 36 and all(s.shape is not None for s in rotated)
    scene = build_scene(slot_map, doc.root, model)
    group = next(g for g in scene.groups if g.rotated)
    assert group.movable and not group.resizable
    template = Template(str(APACHE))
    layers = LayoutLayers(
        LayoutDocument(
            ops=[
                MoveOp(target=group.target, dx=15, dy=-10),
                ResizeOp(target=group.target, width=50, height=50),
            ]
        )
    )
    render = render_for_editor(
        template, None, layers=layers, options=EditorOptions(ctx=None)
    )
    info = next(s for s in render.slots if s.target == group.target)
    assert (info.dx, info.dy) == (15, -10) and not info.resizable
    assert [n.code for n in render.notices] == ["resize_refused"]
    root = etree.fromstring(render.svg_text.encode("utf-8"), make_parser())
    wrapper = next(g for g in root.iter(f"{SVG}g") if g.get("data-jd-op") == "move")
    assert "rotate(" in etree.tostring(
        wrapper, encoding="unicode"
    )  # rotation stays inside


def test_virpil_grouped_move_takes_its_oval_leader_along():
    template = Template(str(VIRPIL))
    before = render_for_editor(template, None)
    slot = next(s for s in before.slots if s.key == "button_5")
    assert slot.edges, "BUTTON_5 has a leader line in this template"
    edge_before = next(e for e in before.edges if e.edge_id == slot.edges[0])
    layers = LayoutLayers(
        LayoutDocument(ops=[MoveOp(target=slot.target, dx=20, dy=10)])
    )
    after = render_for_editor(template, None, layers=layers)
    edge_after = next(e for e in after.edges if e.edge_id == slot.edges[0])
    moved_end = "source" if edge_before.source_slot == slot.target else "target"
    index = 0 if moved_end == "source" else -1
    assert edge_after.points[index] == (
        edge_before.points[index][0] + 20,
        edge_before.points[index][1] + 10,
    )
    other = -1 if index == 0 else 0
    assert edge_after.points[other] == edge_before.points[other]
    root = etree.fromstring(after.svg_text.encode("utf-8"), make_parser())
    markers = [
        e for e in root.iter(f"{SVG}ellipse") if e.get("data-jd-edge") == slot.edges[0]
    ]
    assert markers  # the oval sits at the free end, which did not move
    assert all(m.get("transform") is None for m in markers)
    path = next(
        p for p in root.iter(f"{SVG}path") if p.get("data-jd-edge") == slot.edges[0]
    )
    assert path_endpoints(path.get("d"))[index] == edge_after.points[index]


def test_orion_cell_id_hide_and_boxes_round_trip_through_model():
    template = Template(str(ORION))
    preview = render_for_editor(template, None)
    target = next(s for s in preview.slots if s.key == "button_16")
    assert target.edges
    box_op = AddModifierBoxesOp(target="button_7", count=2)
    layers = LayoutLayers(LayoutDocument(ops=[HideOp(target=target.target), box_op]))
    render = render_for_editor(template, None, layers=layers)
    root = etree.fromstring(render.svg_text.encode("utf-8"), make_parser())
    model = DrawioModel.from_content(root.get("content"))
    cells = model.cells_by_id()
    hidden = [c for c in cells.values() if c.plain_label.lower() == "button_16"]
    assert hidden and not hidden[0].visible
    edge = next(e for e in render.edges if e.edge_id == target.edges[0])
    assert edge.hidden and not cells[edge.edge_id].visible
    added = [c for c in cells.values() if c.style_dict.get("jdAdded")]
    assert [c.label for c in added] == ["BUTTON_7_MODIFIER_1", "BUTTON_7_MODIFIER_2"]
    parent_cell = next(c for c in cells.values() if c.plain_label.lower() == "button_7")
    assert all(c.parent == parent_cell.parent for c in added)
    assert [n.code for n in render.notices] == []


def test_control_panel_background_duplicate_is_not_movable():
    template = Template(str(CONTROL_PANEL))
    render = render_for_editor(template, None)
    button_22 = sorted(
        (s for s in render.slots if s.key == "button_22"), key=lambda s: s.target
    )
    assert len(button_22) == 2
    assert [s.movable for s in button_22] == [
        False,
        True,
    ]  # the page-sized frame first (top-left)
    stacked = [s for s in render.slots if s.stacked > 1]
    assert stacked and all(s.key.startswith("button_") for s in stacked)


def test_editor_render_without_device_keeps_placeholders_and_describes_capabilities():
    template = Template(str(VIRPIL))
    render = render_for_editor(template, None)
    assert render.supported and render.page.width > 0
    assert (
        "BUTTON_5" in render.svg_text and 'data-jd-slot="button_5#1"' in render.svg_text
    )
    payload = render.as_dict()
    assert payload["supported"] and payload["slots"][0]["bbox"]["width"] > 0
    assert all(s.movable and s.resizable for s in render.slots if s.role == "action")
    plain = render_for_editor(template, None, options=EditorOptions(annotate=False))
    assert "data-jd-slot" not in plain.svg_text and len(plain.slots) == len(
        render.slots
    )
