"""Auto-add and Save-as-template dialogs, plus the note dialog (offscreen, no WebEngine)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.db.db_device_management import (  # noqa: E402
    get_device_template_path,
)
from joystick_diagrams.db.layout_service import LayoutService  # noqa: E402
from joystick_diagrams.export import render_template  # noqa: E402
from joystick_diagrams.render import RenderContext  # noqa: E402
from joystick_diagrams.render.editor import render_for_editor  # noqa: E402
from joystick_diagrams.render.layout import TEMPLATE_LAYER, MoveOp  # noqa: E402
from joystick_diagrams.template import Template  # noqa: E402
from joystick_diagrams.ui import strings_layout as S  # noqa: E402
from joystick_diagrams.ui.customise_layout import NoteDialog  # noqa: E402
from joystick_diagrams.ui.device_setup_controller import (  # noqa: E402
    get_export_devices,
)
from joystick_diagrams.ui.layout_auto_add_dialog import AutoAddDialog  # noqa: E402
from joystick_diagrams.ui.layout_editor.planning import SceneCache  # noqa: E402
from joystick_diagrams.ui.layout_editor.session import (  # noqa: E402
    LayoutEditSession,
)
from joystick_diagrams.ui.layout_save_template_dialog import (  # noqa: E402
    SaveTemplateDialog,
)
from tests.ui.layout_fixtures import DEVICE_GUID, seed_layout_state  # noqa: E402

STARTER_KEY = "bundled:Starter Template.svg"


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


@pytest.fixture
def exports():
    seed_layout_state()
    devices = get_export_devices()
    return devices  # F-16C first, Mirage second (same device, same template)


def make_session(template):
    return LayoutEditSession(
        LayoutService(), template.template_key, template.content_hash
    )


@pytest.mark.uitest
def test_auto_add_dialog_summary_and_one_undo_step(qapp, exports):
    f16 = exports[0]
    template = f16.template
    render = render_for_editor(
        template, f16, layers=LayoutService().get_layers(template.template_key, None)
    )
    dialog = AutoAddDialog(
        scene=SceneCache().scene_for(template),
        render=render,
        export_device=f16,
        all_devices=[ed.device for ed in exports],
        scope_text=S.SCOPE_ALL_PROFILES,
    )
    # F-16C: Pickle 3 mods (1 template box → 2 new), Trigger 2, Gear 1 → 5 boxes on 3 controls
    assert dialog.which_this.text() == "Controls with modifiers in F-16C"
    assert dialog.which_any.text().endswith("(3)")
    assert dialog.summary_added.text() == "✓ 5 boxes added to 3 controls"
    assert dialog.add_button.text() == "Add 5 boxes" and dialog.add_button.isEnabled()
    assert not dialog.summary_room.isVisibleTo(dialog)
    assert "Applies to: All profiles on this diagram" in dialog.summary_applies.text()
    assert not dialog.list_extras_under_text()

    dialog.max_spin.setValue(1)
    assert dialog.summary_added.text() == "✓ 2 boxes added to 2 controls"
    dialog.which_any.setChecked(True)
    dialog.max_spin.setValue(4)
    # Mirage adds Radar on BUTTON_2 with 4 modifiers → BUTTON_2 wants 4 boxes,
    # which use up the room BUTTON_3's box had: 2 + 4 placed, Gear left without room
    assert dialog.summary_added.text() == "✓ 6 boxes added to 2 controls"
    assert dialog.summary_room.isVisibleTo(dialog)
    assert dialog.summary_room.text() == "! 1 control doesn't have room for 1 box."
    assert "listed under the main text" in dialog.summary_room_tail.text()
    assert dialog.list_extras_under_text()
    dialog.room_notice.setChecked(True)
    assert "left off and a notice shown" in dialog.summary_room_tail.text()
    assert not dialog.list_extras_under_text()
    indexes = sorted(
        (op.target, box.index) for op in dialog.result_ops() for box in op.boxes
    )
    assert ("button_1#1", 2) in indexes and ("button_1#1", 1) not in indexes
    assert ("button_2#1", 4) in indexes

    session = make_session(template)
    session.apply(dialog.result_ops(), label="auto-add")
    assert len(LayoutService().get_document(template.template_key).ops) == 2
    session.undo()
    assert LayoutService().get_document(template.template_key).ops == []
    # Boxes already added are subtracted next time
    session.redo()
    render = render_for_editor(template, f16, layers=session.layers())
    again = AutoAddDialog(
        scene=SceneCache().scene_for(template),
        render=render,
        export_device=f16,
        all_devices=[ed.device for ed in exports],
        scope_text="x",
    )
    # F-16C's Gear still wants a box but there is no room left for it
    assert again.summary_added.text() == S.AUTO_SUMMARY_NONE_FIT
    assert again.summary_room.isVisibleTo(again)
    assert not again.add_button.isEnabled()


@pytest.mark.uitest
def test_save_as_template_bakes_and_assigns(qapp, exports, tmp_path):
    f16 = exports[0]
    template = f16.template
    session = make_session(template)
    session.move("button_1", 30, 0)
    session.add_modifier_box("button_1", 2, 0, 44, 100, 20)
    session.set_scope(f16.profile_wrapper.profile_key)
    session.hide("button_6")
    session.set_scope(TEMPLATE_LAYER)

    dialog = SaveTemplateDialog(
        template=template,
        session=session,
        export_device=f16,
        device_name="Gladiator NXT",
        device_id=DEVICE_GUID,
        theme=None,
        folder=tmp_path,
    )
    assert dialog.name_edit.text() == "Starter Template – with modifier boxes"
    assert dialog.include_all.text() == "All profiles on this diagram (2 changes)"
    assert dialog.include_profile.text() == "All profiles + F-16C (2 + 1 change)"
    assert not dialog.store_style.isEnabled()
    assert dialog.use_now.text() == "Use it for Gladiator NXT now"
    dialog.include_profile.setChecked(True)
    dialog.save()
    assert dialog.result_text.startswith("✔ Saved to ")  # inline, no dialog
    path = dialog.saved_path
    assert path is not None and path.parent == tmp_path
    assert dialog.assigned and get_device_template_path(DEVICE_GUID) == str(path)
    assert dialog.bake_result.added_boxes == 1 and not dialog.bake_result.skipped_ops

    saved = Template(str(path))
    assert "button_1_modifier_2" in saved.get_template_modifiers()
    assert saved.get_template_buttons() == template.get_template_buttons()
    text = saved.raw_data
    assert "TEMPLATE_NAME" in text and "Pickle" not in text and "data-jd-" not in text
    # the profile-only hide was included
    assert 'display="none"' in text

    class Export:
        def __init__(self):
            self.template = saved
            self.profile_wrapper = f16.profile_wrapper
            self.device = f16.device
            self.template_file_name = saved.template_file_name

    legacy = render_template(Export(), None).svg_text
    dom = render_template(Export(), RenderContext(engine_override="dom")).svg_text
    for out in (legacy, dom):
        assert "Pickle (LCtrl)" in out and "BUTTON_1_MODIFIER_2" not in out


@pytest.mark.uitest
def test_note_dialog_inserts_helpers_instead_of_typed_tokens(qapp):
    dialog = NoteDialog("Hello ")
    dialog.edit.setCursorPosition(len("Hello "))
    dialog.insert_profile.click()
    dialog.edit.insert(" · ")
    dialog.insert_date.click()
    assert dialog.text() == "Hello PROFILE_NAME · CURRENT_DATE"


@pytest.mark.uitest
def test_save_dialog_profile_option_disabled_without_profile_changes(qapp, exports):
    f16 = exports[0]
    session = make_session(f16.template)
    session.apply([MoveOp(target="button_1", dx=1, dy=1)])
    dialog = SaveTemplateDialog(
        template=f16.template,
        session=session,
        export_device=f16,
        device_name="D",
        device_id=DEVICE_GUID,
    )
    assert not dialog.include_profile.isEnabled()
    assert dialog.include_all.isChecked()
