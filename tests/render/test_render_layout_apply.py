"""Layout stage on fixtures: every op, leader-line follow, model mirror, annotations."""

from datetime import datetime

import pytest
from lxml import etree

from joystick_diagrams.input.button import Button
from joystick_diagrams.render import (
    BindingOptions,
    RenderContext,
    RenderNotice,
    render_device,
)
from joystick_diagrams.render.adapters.edge_mapping import path_endpoints
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.layout import (
    AddModifierBoxesOp,
    AddModifierBoxOp,
    AddNoteOp,
    HideOp,
    LayoutDocument,
    MoveEdgeEndOp,
    MoveOp,
    ResizeOp,
)
from tests.render.render_fixtures import (
    CellSpec,
    DrawioFixture,
    EdgeSpec,
    basic_fixture,
    build_svg,
    export_device_for,
    new_device,
)

NOW = datetime(2026, 1, 2)
SVG = "{http://www.w3.org/2000/svg}"
KEY = "bundled:fixture.svg"


class KeyedTemplate:
    template_key = KEY
    content_hash = "hash-1"

    def __init__(self, raw_data: str) -> None:
        self.raw_data = raw_data


def device():
    dev = new_device()
    dev.create_input(Button(1), "Fire")
    for key in ("LShift", "LCtrl", "LAlt"):
        dev.add_modifier_to_input(Button(1), {key}, f"Alt {key}")
    dev.create_input(Button(2), "Two")
    return dev


def render(text, ops, *, preview=False, profile_ops=(), content_hash="hash-1"):
    ed = export_device_for(text, device())
    template = KeyedTemplate(text)
    template.content_hash = content_hash
    ed.template = template
    layouts = {(KEY, ""): LayoutDocument(ops=list(ops), content_hash="hash-1")}
    if profile_ops:
        layouts[(KEY, "profile_1")] = LayoutDocument(ops=list(profile_ops))
        ed.profile_wrapper.profile_key = "profile_1"
    ctx = RenderContext(
        now=NOW, layouts=layouts, preview=preview, engine_override="dom"
    )
    options = BindingOptions(False, " | ", "%d/%m/%Y", now=NOW)
    outcome = render_device(ed, ctx, options)
    root = etree.fromstring(outcome.svg_text.encode("utf-8"), make_parser())
    return outcome, root, DrawioModel.from_content(root.get("content")).cells_by_id()


def wrappers(root):
    return [g for g in root.iter(f"{SVG}g") if g.get("data-jd-op")]


def edge_fixture(variant="flat"):
    """b1 (10,50) with an edge to b1m1 (10,90) and a free edge near b2 (10,170)."""
    fx = basic_fixture(variant)
    fx.edges = [
        EdgeSpec("e_both", "b1", "b1m1", d="M 57 91 L 57 101"),
        EdgeSpec("e_src", "b2", "", d="M 97 196 L 97 262"),
        EdgeSpec(
            "e_free", "", "", d="M 190 185 L 250 150"
        ),  # starts 3px from ax (107,181,80,30)
    ]
    return fx


@pytest.mark.parametrize("variant", ["flat", "grouped", "cellid"])
def test_move_wraps_shape_and_label_and_mirrors_model(variant):
    outcome, root, cells = render(
        build_svg(basic_fixture(variant)), [MoveOp(target="button_2", dx=30, dy=40)]
    )
    assert outcome.report.skipped_ops == ()
    (wrapper,) = wrappers(root)
    assert wrapper.get("transform") == "translate(30 40)"
    tags = [etree.QName(c).localname for c in wrapper.iter() if c is not wrapper]
    assert "rect" in tags and "switch" in tags  # shape and label travel together
    assert cells["b2"].geometry.x == 40 and cells["b2"].geometry.y == 210
    assert "Two" in "".join(wrapper.itertext())


def test_resize_updates_rect_label_and_model_and_refuses_non_rect():
    fx = basic_fixture()
    fx.cells.append(CellSpec("nobox", "BUTTON_9", 300, 100, shape="none"))
    ops = [
        ResizeOp(target="button_1", width=120, height=40),
        ResizeOp(target="button_9", width=50, height=50),
    ]
    outcome, root, cells = render(build_svg(fx), ops)
    rect = next(
        r
        for r in root.iter(f"{SVG}rect")
        if r.get("x") == "17.0" and r.get("y") == "61.0"
    )
    assert (rect.get("width"), rect.get("height")) == ("120", "40")
    label = rect.getnext()
    outer = label.find(".//{http://www.w3.org/1999/xhtml}div")
    assert "width: 118px" in outer.get("style") and "padding-top: 81px" in outer.get(
        "style"
    )
    text = label.find(f".//{SVG}text")
    assert (text.get("x"), text.get("y")) == ("77", "85")  # centre moved by (20, 5)
    assert (cells["b1"].geometry.width, cells["b1"].geometry.height) == (120, 40)
    assert outcome.report.skipped_ops == (ops[1].uid,)
    assert RenderNotice.LAYOUT_OPS_SKIPPED in outcome.report.notices


def test_hide_hides_slot_and_exclusive_edges_and_model():
    fx = edge_fixture()
    outcome, root, cells = render(build_svg(fx), [HideOp(target="button_2")])
    (wrapper,) = wrappers(root)
    assert wrapper.get("display") == "none"
    assert not cells["b2"].visible
    paths = {p.get("d"): p for p in root.iter(f"{SVG}path")}
    assert paths["M 97 196 L 97 262"].get("display") == "none"  # only attached to b2
    assert not cells["e_src"].visible
    assert paths["M 57 91 L 57 101"].get("display") is None  # b1 ↔ b1m1 untouched


def test_hide_keeps_edge_whose_other_end_is_visible():
    outcome, root, cells = render(
        build_svg(edge_fixture()), [HideOp(target="button_1")]
    )
    paths = {p.get("d"): p for p in root.iter(f"{SVG}path")}
    assert paths["M 57 91 L 57 101"].get("display") is None
    assert cells["e_both"].visible


@pytest.mark.parametrize("variant", ["flat", "cellid"])
def test_edges_follow_source_target_both_and_free_ends(variant):
    ops = [
        MoveOp(target="button_1", dx=10, dy=0),  # source of e_both
        MoveOp(
            target="button_1_modifier_1", dx=10, dy=0
        ),  # target of e_both → whole line
        MoveOp(target="button_2", dx=0, dy=20),  # source-only edge e_src
        MoveOp(target="axis_x", dx=5, dy=5),  # nearest template slot of e_free's start
    ]
    outcome, root, cells = render(build_svg(edge_fixture(variant)), ops)
    assert outcome.report.skipped_ops == ()
    ends = {}
    for path in root.iter(f"{SVG}path"):
        if path.get("pointer-events") == "stroke":
            start, end = path_endpoints(path.get("d"))
            ends[(round(start[0]), round(start[1]), round(end[0]), round(end[1]))] = (
                path
            )
    assert (67, 91, 67, 101) in ends  # both ends moved
    assert (97, 216, 97, 262) in ends  # only the attached source end moved
    # The free end followed the nearest slot and was clamped onto its border (192 = 187 + 5).
    assert (192, 190, 250, 150) in ends
    points = {
        p.get("as"): (float(p.get("x")), float(p.get("y")))
        for p in cells["e_free"].element.iter("mxPoint")
    }
    assert points["sourcePoint"] == (
        185.0,
        179.0,
    )  # created in model coords: (192-7, 190-11)
    assert "targetPoint" not in points  # the untouched free end needs no point


def test_free_edge_end_is_not_attached_when_two_slots_tie():
    fx = basic_fixture()
    # Start point exactly between b1m1 (17,101,80,30) and b1m1k (107,101,...): x=102 is 5px from both.
    fx.edges = [EdgeSpec("tie", "", "", d="M 102 116 L 102 60")]
    outcome, root, _cells = render(
        build_svg(fx), [MoveOp(target="button_1_modifier_1", dx=10, dy=0)]
    )
    assert any(p.get("d") == "M 102 116 L 102 60" for p in root.iter(f"{SVG}path"))


def test_move_edge_end_op_moves_free_end_and_model_point():
    fx = edge_fixture()
    uid = "e_src"
    outcome, root, cells = render(
        build_svg(fx), [MoveEdgeEndOp(edge=uid, end="target", dx=10, dy=-6)]
    )
    assert any(p.get("d") == "M 97 196 L 107 256" for p in root.iter(f"{SVG}path"))
    points = {
        p.get("as"): (float(p.get("x")), float(p.get("y")))
        for p in cells[uid].element.iter("mxPoint")
    }
    assert points["targetPoint"] == (
        100.0,
        245.0,
    )  # created from the rendered end (97-7, 262-11) + delta


def test_group_ancestor_edge_follows_only_when_every_child_moves():
    fx = basic_fixture()
    fx.cells.insert(
        0,
        CellSpec(
            "grp", "", 0, 0, 300, 300, style="group", shape="none", rendered=False
        ),
    )
    for cell in fx.cells:
        if cell.id in ("b1", "b2"):
            cell.parent = "grp"
    line = "M 50 225 L 60 120"
    fx.edges = [EdgeSpec("e_grp", "plain", "grp", d=line)]
    raw = build_svg(fx)
    # Only b1 moves: the edge attached to the group must stay.
    _o, root, _c = render(raw, [MoveOp(target="button_1", dx=10, dy=10)])
    assert any(p.get("d") == line for p in root.iter(f"{SVG}path"))
    # Both children move by the same delta: the group end follows.
    _o, root, cells = render(
        raw,
        [
            MoveOp(target="button_1", dx=10, dy=10),
            MoveOp(target="button_2", dx=10, dy=10),
        ],
    )
    assert any(p.get("d") == "M 50 225 L 70 130" for p in root.iter(f"{SVG}path"))
    assert cells["b1"].geometry.x == 20  # child geometry stays relative to the group


def test_stacked_duplicates_share_an_identity_and_move_together():
    fx = basic_fixture()
    fx.cells.append(
        CellSpec("b2dup", "BUTTON_2", 12, 172)
    )  # overlaps b2 (10,170) by > 80 %
    fx.cells.append(
        CellSpec("b2far", "BUTTON_2", 300, 240)
    )  # a second place for the same key
    outcome, root, cells = render(
        build_svg(fx), [MoveOp(target="button_2", dx=5, dy=5)], preview=True
    )
    moved = wrappers(root)
    assert len(moved) == 2 and all(
        w.get("transform") == "translate(5 5)" for w in moved
    )
    assert cells["b2"].geometry.x == 15 and cells["b2dup"].geometry.x == 17
    assert cells["b2far"].geometry.x == 300
    targets = {g.get("data-jd-slot") for g in root.iter() if g.get("data-jd-slot")}
    assert {"button_2#1", "button_2#2"} <= targets and "button_2#3" not in targets


def test_add_modifier_boxes_creates_filled_slots_and_cells():
    op = AddModifierBoxesOp(target="button_1", count="auto", max_count=4)
    outcome, root, cells = render(build_svg(basic_fixture()), [op])
    assert (
        dict(outcome.report.overflow) == {}
    )  # template had 1 box, 2 were added for 3 modifiers
    added = [c for c in cells.values() if (c.id or "").startswith("jd-")]
    assert [c.label for c in added] == ["Alt LCtrl - LCtrl", "Alt LAlt - LAlt"]
    assert all(c.style_dict.get("jdAdded") == "1" and c.parent == "1" for c in added)
    assert {c.id for c in added} == {f"jd-{op.uid}:2", f"jd-{op.uid}:3"}
    texts = [t.text for t in root.iter(f"{SVG}text") if t.text]
    assert "Alt LCtrl - LCtrl" in texts and "Alt LAlt - LAlt" in texts
    baseline = render(build_svg(basic_fixture()), [])[1]
    assert (
        len(list(root.iter(f"{SVG}rect"))) == len(list(baseline.iter(f"{SVG}rect"))) + 2
    )


def test_explicit_box_geometry_is_relative_to_parent_and_follows_it():
    box = AddModifierBoxOp(target="button_1", index=2, dx=0, dy=40, width=60, height=20)
    outcome, root, cells = render(
        build_svg(basic_fixture()), [MoveOp(target="button_1", dx=100, dy=0), box]
    )
    cell = cells[f"jd-{box.uid}"]
    assert (
        cell.geometry.x == 110 and cell.geometry.y == 90
    )  # parent (10,50) moved by 100
    rect = next(r for r in root.iter(f"{SVG}rect") if r.get("width") == "60")
    assert (rect.get("x"), rect.get("y")) == ("117", "101")
    assert cell.label == "Alt LCtrl - LCtrl"


def test_box_content_key_and_action():
    ops = [
        AddModifierBoxOp(
            target="button_1", index=2, dx=0, dy=40, width=60, height=20, content="key"
        ),
        AddModifierBoxOp(
            target="button_1",
            index=3,
            dx=70,
            dy=40,
            width=60,
            height=20,
            content="action",
        ),
    ]
    _o, _root, cells = render(build_svg(basic_fixture()), ops)
    assert cells[f"jd-{ops[0].uid}"].label == "LCtrl"
    assert cells[f"jd-{ops[1].uid}"].label == "Alt LAlt"


def test_add_note_resolves_tokens_and_adds_model_cell():
    note = AddNoteOp(
        text="PROFILE_NAME · CURRENT_DATE", x=250, y=250, width=120, height=24
    )
    outcome, root, cells = render(build_svg(basic_fixture()), [note])
    assert "profile_1 · 02/01/2026" in [t.text for t in root.iter(f"{SVG}text")]
    cell = cells[f"jd-{note.uid}"]
    assert cell.label == "profile_1 · 02/01/2026"
    assert (
        cell.style_dict.get("jdNote") == "1" and cell.geometry.x == 243
    )  # 250 - render offset 7


def test_anchored_note_follows_its_slot():
    note = AddNoteOp(text="n", x=0, y=-30, width=50, height=10, anchor="button_2")
    _o, root, cells = render(
        build_svg(basic_fixture()), [MoveOp(target="button_2", dx=10, dy=0), note]
    )
    assert (
        cells[f"jd-{note.uid}"].geometry.x == 20
    )  # b2 at 10, moved 10, minus offset 7 → 13 + 7


def test_missing_slot_is_skipped_with_notice_and_other_ops_apply():
    ops = [MoveOp(target="button_77", dx=1, dy=1), HideOp(target="button_2")]
    outcome, root, cells = render(build_svg(basic_fixture()), ops)
    assert outcome.report.skipped_ops == (ops[0].uid,)
    assert RenderNotice.LAYOUT_OPS_SKIPPED in outcome.report.notices
    assert not cells["b2"].visible


def test_profile_layer_applies_after_template_layer():
    outcome, root, cells = render(
        build_svg(basic_fixture()),
        [MoveOp(target="button_2", dx=10, dy=0)],
        profile_ops=[MoveOp(target="button_2", dx=0, dy=10)],
    )
    assert (cells["b2"].geometry.x, cells["b2"].geometry.y) == (20, 180)


def test_drift_notice_when_content_hash_differs():
    outcome, _root, _cells = render(
        build_svg(basic_fixture()), [HideOp(target="button_2")], content_hash="other"
    )
    assert RenderNotice.TEMPLATE_UPDATED in outcome.report.notices
    outcome, _root, _cells = render(
        build_svg(basic_fixture()), [HideOp(target="button_2")]
    )
    assert RenderNotice.TEMPLATE_UPDATED not in outcome.report.notices


def test_text_only_template_refuses_layout_ops():
    fx = DrawioFixture(
        cells=[CellSpec("x", "something else", rendered_html="BUTTON_1")]
    )
    ops = [MoveOp(target="button_1", dx=1, dy=1)]
    outcome, root, _cells = render(build_svg(fx), ops)
    assert RenderNotice.LAYOUT_UNSUPPORTED in outcome.report.notices
    assert outcome.report.skipped_ops == (ops[0].uid,)
    assert wrappers(root) == []


def test_preview_annotations_cover_slots_added_elements_and_edges():
    box = AddModifierBoxOp(target="button_1", index=2, dx=0, dy=40, width=60, height=20)
    outcome, root, _cells = render(
        build_svg(edge_fixture("cellid")), [box], preview=True
    )
    slots = {e.get("data-jd-slot") for e in root.iter() if e.get("data-jd-slot")}
    assert {"button_1#1", "button_2#1", "axis_x#1", box.uid} <= slots
    assert {e.get("data-jd-edge") for e in root.iter() if e.get("data-jd-edge")} == {
        "e_both",
        "e_src",
        "e_free",
    }
    added = [e for e in root.iter() if e.get("data-jd-added") == box.uid]
    assert len(added) == 2 and {e.get("data-jd-role") for e in added} == {"modifier"}
    assert any(
        e.get("data-jd-role") == "action"
        for e in root.iter()
        if e.get("data-jd-slot") == "button_1#1"
    )
    # Without preview nothing is annotated.
    _o, plain_root, _c = render(build_svg(edge_fixture("cellid")), [box])
    assert not any(e.get("data-jd-slot") for e in plain_root.iter())


def test_no_ops_leaves_document_untouched():
    text = build_svg(basic_fixture())
    ed = export_device_for(text, device())
    ctx = RenderContext(now=NOW, engine_override="dom")
    options = BindingOptions(False, " | ", "%d/%m/%Y", now=NOW)
    outcome = render_device(ed, ctx, options)
    assert "data-jd" not in outcome.svg_text and "jd-" not in outcome.svg_text
