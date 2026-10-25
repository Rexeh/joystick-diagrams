"""Layout op model: parsing, JSON round-trip, targets and the effective-state fold."""

import pytest
from pydantic import ValidationError

from joystick_diagrams.render.layout import (
    SCHEMA_VERSION,
    AddModifierBoxesOp,
    AddModifierBoxOp,
    AddNoteOp,
    EditNoteOp,
    HideOp,
    LayoutDocument,
    LayoutLayers,
    MoveEdgeEndOp,
    MoveOp,
    RemoveAddedElementOp,
    ResetSlotOp,
    ResizeOp,
    ShowOp,
    fold_ops,
    format_target,
    parse_op,
    parse_target,
)


def test_targets_normalise_case_and_duplicate_index():
    assert parse_target("BUTTON_1") == ("button_1", 1)
    assert parse_target("Button_1#3") == ("button_1", 3)
    assert parse_target("button_1#0") == ("button_1", 1)
    assert format_target("BUTTON_2", 2) == "button_2#2"
    assert MoveOp(target="BUTTON_1", dx=1, dy=2).target == "button_1#1"
    uid = "0123456789abcdef0123456789abcdef"
    assert HideOp(target=uid).target == uid  # added-element uids are kept verbatim


def test_parse_op_from_dict_and_json_and_rejects_unknown():
    op = parse_op({"op": "move", "target": "button_1", "dx": 12.5, "dy": -3})
    assert isinstance(op, MoveOp) and op.dx == 12.5 and len(op.uid) == 32
    note = parse_op(
        '{"op": "add_note", "text": "hi", "x": 1, "y": 2, "width": 10, "height": 5}'
    )
    assert isinstance(note, AddNoteOp) and note.style.font_size == 12
    with pytest.raises(ValidationError):
        parse_op({"op": "teleport", "target": "button_1"})
    with pytest.raises(ValidationError):
        parse_op({"op": "resize", "target": "button_1", "width": 0, "height": 10})
    with pytest.raises(ValidationError):
        parse_op({"op": "move", "target": "button_1", "dx": 1, "dy": 2, "extra": 1})
    with pytest.raises(ValidationError):
        parse_op({"op": "add_modifier_boxes", "target": "button_1", "count": 0})


def test_document_round_trips_json_with_every_op_kind():
    ops = [
        MoveOp(target="button_1", dx=1, dy=2),
        ResizeOp(target="button_1", width=100, height=20),
        HideOp(target="button_2", hide_leaders=False),
        ShowOp(target="button_2"),
        AddModifierBoxesOp(
            target="button_1",
            count=2,
            boxes=[{"index": 2, "dx": 0, "dy": 30, "width": 90, "height": 20}],
        ),
        AddModifierBoxesOp(target="button_3", count="auto", arrangement="right"),
        AddModifierBoxOp(target="button_1", index=4, dx=5, dy=5, content="key"),
        AddNoteOp(
            text="PROFILE_NAME", x=1, y=1, width=50, height=10, anchor="BUTTON_1"
        ),
        EditNoteOp(target="0123456789abcdef0123456789abcdef", text="changed"),
        RemoveAddedElementOp(target="0123456789abcdef0123456789abcdef"),
        MoveEdgeEndOp(edge="cell-9", end="target", dx=3, dy=4),
        ResetSlotOp(target="button_9"),
    ]
    doc = LayoutDocument(template_key="bundled:x.svg", content_hash="abc", ops=ops)
    back = LayoutDocument.model_validate_json(doc.model_dump_json())
    assert back.schema_version == SCHEMA_VERSION
    assert [type(op) for op in back.ops] == [type(op) for op in ops]
    assert [op.uid for op in back.ops] == [op.uid for op in ops]
    assert back.ops[4].boxes[0].uid == ops[4].boxes[0].uid
    assert back.ops[7].anchor == "button_1#1"
    assert back.content_hash == "abc"


def test_document_remove_replace_and_coalesce():
    doc = LayoutDocument()
    first = doc.coalesce_move(MoveOp(target="button_1", dx=1, dy=0))
    merged = doc.coalesce_move(MoveOp(target="button_1", dx=2, dy=3))
    assert (
        len(doc.ops) == 1
        and merged.uid == first.uid
        and (merged.dx, merged.dy) == (3, 3)
    )
    doc.coalesce_move(MoveOp(target="button_2", dx=1, dy=1))
    assert len(doc.ops) == 2
    hide = doc.append(HideOp(target="button_2"))
    assert doc.replace_op(hide.uid, ShowOp(target="button_2", uid=hide.uid))
    assert isinstance(doc.find(hide.uid), ShowOp)
    assert doc.remove_op(hide.uid) and doc.find(hide.uid) is None
    assert not doc.remove_op("missing")


def test_fold_sums_moves_keeps_last_size_and_hidden_flag():
    ops = [
        MoveOp(target="button_1", dx=10, dy=0),
        MoveOp(target="button_1", dx=-4, dy=5),
        ResizeOp(target="button_1", width=50, height=10),
        ResizeOp(target="button_1", width=60, height=12),
        HideOp(target="button_1"),
        ShowOp(target="button_1"),
        HideOp(target="button_2", hide_leaders=False),
    ]
    effective = fold_ops(ops)
    state = effective.slots["button_1#1"]
    assert (state.dx, state.dy) == (6, 5)
    assert state.size == (60, 12)
    assert state.hidden is False
    assert state.op_uids == [op.uid for op in ops[:6]]
    assert (
        effective.slots["button_2#1"].hidden
        and not effective.slots["button_2#1"].hide_leaders
    )
    assert set(effective.changed_slots()) == {"button_1#1", "button_2#1"}


def test_fold_added_elements_and_reset():
    boxes = AddModifierBoxesOp(
        target="button_1",
        count=1,
        boxes=[{"index": 2, "dx": 0, "dy": 30, "width": 90, "height": 20}],
    )
    box_uid = boxes.boxes[0].uid
    single = AddModifierBoxOp(target="button_1", index=3, dx=0, dy=60)
    note = AddNoteOp(text="n", x=1, y=1, width=10, height=10)
    auto = AddModifierBoxesOp(target="button_2", count="auto")
    ops = [
        boxes,
        single,
        note,
        auto,
        MoveOp(target=box_uid, dx=5, dy=5),
        HideOp(target=single.uid),
        EditNoteOp(target=note.uid, text="edited"),
        MoveOp(target="button_1", dx=1, dy=1),
    ]
    effective = fold_ops(ops)
    assert (
        effective.added[box_uid].state.dx == 5 and effective.added[box_uid].index == 2
    )
    assert effective.added[single.uid].state.hidden
    assert effective.added[note.uid].text == "edited"
    assert effective.auto_boxes == [auto]
    assert auto.box_uid(1) == f"{auto.uid}:1"
    assert boxes.box_uid(2) == box_uid

    effective = fold_ops([*ops, RemoveAddedElementOp(target=note.uid)])
    assert note.uid not in effective.added

    effective = fold_ops([*ops, ResetSlotOp(target="button_1")])
    assert "button_1#1" not in effective.slots
    assert box_uid not in effective.added and single.uid not in effective.added
    assert note.uid in effective.added  # the note is not anchored to button_1
    effective = fold_ops([*ops, ResetSlotOp(target="button_2")])
    assert effective.auto_boxes == []


def test_fold_edge_end_deltas_accumulate():
    effective = fold_ops(
        [
            MoveEdgeEndOp(edge="e1", end="target", dx=1, dy=2),
            MoveEdgeEndOp(edge="e1", end="target", dx=3, dy=4),
            MoveEdgeEndOp(edge="e1", end="source", dx=1, dy=1),
        ]
    )
    assert effective.edge_ends == {("e1", "target"): (4, 6), ("e1", "source"): (1, 1)}


def test_layers_order_and_attribution():
    template_op = MoveOp(target="button_1", dx=1, dy=0)
    profile_op = MoveOp(target="button_1", dx=0, dy=1)
    layers = LayoutLayers(
        LayoutDocument(ops=[template_op]), LayoutDocument(ops=[profile_op])
    )
    assert [op.uid for op in layers.all_ops()] == [template_op.uid, profile_op.uid]
    assert layers.layer_of(template_op.uid) == "template"
    assert layers.layer_of(profile_op.uid) == "profile"
    assert layers.layer_of("nope") is None
    assert not layers.is_empty and LayoutLayers().is_empty
