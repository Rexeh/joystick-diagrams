"""``LayoutEditSession``: persistence through ``LayoutService``, undo/redo, scopes.

Uses the real service on the throwaway database from ``tests/ui/conftest.py``.
"""

from joystick_diagrams.db.layout_service import LayoutService
from joystick_diagrams.render.layout import (
    TEMPLATE_LAYER,
    AddModifierBoxesOp,
    HideOp,
    MoveOp,
    RemoveAddedElementOp,
    ResizeOp,
)
from joystick_diagrams.ui.layout_editor.session import LayoutEditSession

KEY = "bundled:Starter Template.svg"
PROFILE = "dcs world_f-16c"


def session(scope: str = TEMPLATE_LAYER) -> LayoutEditSession:
    service = LayoutService()
    return LayoutEditSession(service, KEY, "hash-1", profile_key=PROFILE, scope=scope)


def stored_ops(sess: LayoutEditSession, layer: str = TEMPLATE_LAYER):
    return LayoutService().get_document(KEY, layer).ops  # fresh cache = from the DB


def test_move_persists_immediately_and_undo_redo_round_trip():
    sess = session()
    sess.move("BUTTON_1", 12, -3)
    ops = stored_ops(sess)
    assert len(ops) == 1 and isinstance(ops[0], MoveOp)
    assert ops[0].target == "button_1#1" and ops[0].dx == 12
    assert sess.can_undo and not sess.can_redo

    assert sess.undo() is not None
    assert stored_ops(sess) == []
    assert sess.can_redo
    assert sess.redo() is not None
    assert [op.uid for op in stored_ops(sess)] == [ops[0].uid]


def test_nudges_coalesce_into_one_undo_step_but_drags_do_not():
    sess = session()
    sess.move("button_1", 1, 0, coalesce=True)
    sess.move("button_1", 1, 0, coalesce=True)
    sess.move("button_1", 0, 2, coalesce=True)
    ops = stored_ops(sess)
    assert len(ops) == 1 and (ops[0].dx, ops[0].dy) == (2, 2)
    sess.move("button_1", 5, 5)  # a drag: separate step
    assert len(stored_ops(sess)) == 2
    sess.undo()
    assert len(stored_ops(sess)) == 1
    sess.undo()
    assert stored_ops(sess) == []


def test_resize_with_top_left_shift_is_one_step_of_two_ops():
    sess = session()
    sess.resize("button_1", 150, 40, dx=-10, dy=0)
    ops = stored_ops(sess)
    assert [type(op) for op in ops] == [MoveOp, ResizeOp]
    sess.undo()
    assert stored_ops(sess) == []


def test_scope_sends_ops_to_the_profile_layer_and_layers_combine():
    sess = session(scope=PROFILE)
    sess.hide("button_5")
    assert stored_ops(sess, TEMPLATE_LAYER) == []
    profile_ops = stored_ops(sess, PROFILE)
    assert len(profile_ops) == 1 and isinstance(profile_ops[0], HideOp)
    sess.set_scope(TEMPLATE_LAYER)
    sess.move("button_2", 4, 4)
    layers = sess.layers()
    assert [op.op for op in layers.all_ops()] == ["move", "hide"]
    assert layers.layer_of(profile_ops[0].uid) == "profile"
    assert sess.change_count(PROFILE) == 1 and sess.change_count(TEMPLATE_LAYER) == 1


def test_apply_many_ops_is_one_undo_step():
    sess = session()
    ops = [
        AddModifierBoxesOp(
            target="button_1",
            count=1,
            boxes=[{"index": 2, "dx": 0, "dy": 44, "width": 100, "height": 20}],
        ),
        AddModifierBoxesOp(
            target="button_2",
            count=1,
            boxes=[{"index": 1, "dx": 0, "dy": 44, "width": 100, "height": 20}],
        ),
    ]
    sess.apply(ops, label="auto-add")
    assert len(stored_ops(sess)) == 2
    sess.undo()
    assert stored_ops(sess) == []
    sess.redo()
    assert len(stored_ops(sess)) == 2


def test_added_elements_notes_and_removal():
    sess = session()
    box = sess.add_modifier_box("button_1", 2, 0, 44, 100, 20)
    note = sess.add_note("PROFILE_NAME", 10, 10, 200, 24)
    sess.edit_note(note.uid, "Hello")
    sess.remove_added(box.uid)
    ops = stored_ops(sess)
    assert [op.op for op in ops] == [
        "add_modifier_box",
        "add_note",
        "edit_note",
        "remove_added",
    ]
    assert isinstance(ops[-1], RemoveAddedElementOp) and ops[-1].target == box.uid
    assert ops[2].target == note.uid and ops[2].text == "Hello"


def test_undo_changes_to_a_box_drops_only_its_ops():
    sess = session()
    sess.move("button_1", 1, 1)
    sess.move("button_2", 2, 2)
    sess.add_modifier_box("button_1", 2, 0, 44, 100, 20)
    assert sess.undo_changes_to("BUTTON_1") is not None
    ops = stored_ops(sess)
    assert len(ops) == 1 and ops[0].target == "button_2#1"
    assert sess.undo_changes_to("button_7") is None
    sess.undo()
    assert len(stored_ops(sess)) == 3


def test_clear_layer_and_reset_all_are_undoable():
    sess = session(scope=PROFILE)
    sess.move("button_1", 1, 1)
    sess.set_scope(TEMPLATE_LAYER)
    sess.move("button_2", 1, 1)
    assert sess.clear_layer(PROFILE) is not None
    assert stored_ops(sess, PROFILE) == [] and len(stored_ops(sess)) == 1
    sess.undo()
    assert len(stored_ops(sess, PROFILE)) == 1
    assert sess.reset_all() is not None
    assert sess.service.layers_of_template(KEY) == []
    sess.undo()
    assert sorted(sess.service.layers_of_template(KEY)) == [TEMPLATE_LAYER, PROFILE]
    assert sess.clear_layer("nothing-here") is None
