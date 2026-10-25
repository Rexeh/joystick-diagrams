"""4. Diagrams › Export: rows from device_status, ticks, folder ask, queue, result."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams import workflow_settings  # noqa: E402
from joystick_diagrams.ui import strings_diagrams as S  # noqa: E402
from joystick_diagrams.ui.device_setup import (  # noqa: E402
    build_export_model,
    controller_key,
    tick_key,
)
from joystick_diagrams.ui.diagrams_page import DiagramsPage  # noqa: E402
from joystick_diagrams.ui.stage_contract import STAGE_CONTROLLERS  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    PANEL,
    STICK,
    THROTTLE,
    FakeShell,
    _reset_app_state,
    seed_state,
    settings_store,
)

DIALOG = "joystick_diagrams.ui.export_settings.QFileDialog.getExistingDirectory"
F16 = "dcs world_f-16c"
A10 = "dcs world_a-10c"


def wait_for_export(qapp, screen, timeout=20.0):
    start = time.time()
    while screen.is_exporting and time.time() - start < timeout:
        qapp.processEvents()
        time.sleep(0.01)
    assert not screen.is_exporting


@pytest.fixture
def stage(qapp, settings_store):
    seed_state()
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    return page, shell


@pytest.mark.uitest
def test_rows_come_from_device_status(stage):
    page, _shell = stage
    model = page.export_screen.model
    assert [r.name for r in model.rows] == ["Gladiator NXT", "Warthog Throttle"]
    stick = model.row(controller_key(STICK))
    # Button 99 has no box on the Starter Template
    assert stick.gaps == 1 and stick.missing_controls == ["button_99"]
    assert [n.guid for n in model.not_included] == [PANEL]
    assert model.not_included[0].text == "Not included: Button Box · no template yet"
    assert page.export_screen.export_count() == 4  # every ready profile ticked


@pytest.mark.uitest
def test_no_diagram_line_and_change_deep_link(qapp, settings_store):
    state = seed_state()
    state.device_service.set_make_diagram(PANEL, False, "Button Box")
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    screen = page.export_screen
    assert screen.model.no_diagram == [(PANEL, "Button Box", "set by you")]
    assert screen.no_diagram_label.text().startswith(
        "No diagram: Button Box (set by you)"
    )
    seen = []
    screen.request_stage.connect(lambda i, p: seen.append((i, p)))
    screen.no_diagram_change.click()
    assert seen == [(STAGE_CONTROLLERS, {"device_guid": PANEL})]


@pytest.mark.uitest
def test_ticks_are_remembered(qapp, settings_store):
    seed_state()
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    screen = page.export_screen
    screen.export_list.set_ticks({tick_key(controller_key(STICK), F16)}, False)
    assert screen.export_count() == 1
    assert (
        workflow_settings.get_export_ticks()[tick_key(controller_key(STICK), A10)]
        is False
    )
    shell2 = FakeShell()
    again = DiagramsPage(shell2)
    again.refresh()
    assert again.export_screen.export_count() == 1
    assert again.next_action().label == "Export 1 diagram"
    again.export_screen.export_list.tick_all()
    assert again.export_screen.export_count() == 4


@pytest.mark.uitest
def test_first_export_asks_for_a_folder_once(stage, qapp, tmp_path):
    page, shell = stage
    screen = page.export_screen
    assert screen.export_settings_widget.folder_label.text() == S.SAVE_TO_UNSET
    with patch(DIALOG, return_value=str(tmp_path)) as dialog:
        page.next_action().callback()
        wait_for_export(qapp, screen)
    assert dialog.call_count == 1
    assert workflow_settings.get_export_folder() == tmp_path
    assert len(list(tmp_path.glob("*.svg"))) == 4
    assert screen.export_settings_widget.folder_label.text() == str(tmp_path)
    with patch(DIALOG, return_value="") as dialog:
        page.export()
        wait_for_export(qapp, screen)
    assert dialog.call_count == 0  # remembered
    assert any(text.startswith("Exporting") for text, _p in shell.status)


@pytest.mark.uitest
def test_missing_folder_is_asked_again(stage, qapp, tmp_path):
    page, _shell = stage
    gone = tmp_path / "unplugged"
    workflow_settings.set_export_folder(gone)
    new = tmp_path / "new"
    new.mkdir()
    with patch(
        "joystick_diagrams.ui.export_page.ask_again_for_folder", return_value=new
    ) as ask:
        page.export()
        wait_for_export(qapp, page.export_screen)
    ask.assert_called_once()
    assert ask.call_args.args[1] == str(gone)
    assert len(list(new.glob("*.svg"))) == 4


@pytest.mark.uitest
def test_folder_gone_dialog_is_pre_filled(qapp, settings_store, tmp_path):
    from joystick_diagrams.ui.export_page import FolderGoneDialog

    dialog = FolderGoneDialog(str(tmp_path / "gone"))
    assert dialog.path_edit.text() == str(tmp_path / "gone")
    assert dialog.windowTitle() == S.FOLDER_GONE_TITLE.format(folder=tmp_path / "gone")
    assert dialog.export_here.text() == S.EXPORT_HERE


@pytest.mark.uitest
def test_export_queues_while_reading(stage, qapp, tmp_path):
    page, shell = stage
    tmp_path = tmp_path / "out"
    tmp_path.mkdir()
    workflow_settings.set_export_folder(tmp_path)
    shell.read_in_progress = True
    action = page.next_action()
    assert action.label == S.EXPORT_WHEN_READ_FINISHES
    action.callback()
    assert page.export_screen.queued
    assert page.footer_hint() == S.EXPORT_QUEUED_HINT
    assert not page.next_action().enabled
    assert list(tmp_path.iterdir()) == []
    shell.read_in_progress = False
    shell.read_finished.emit(None)
    start = time.time()
    while not list(tmp_path.glob("*.svg")) and time.time() - start < 10:
        qapp.processEvents()
        time.sleep(0.01)
    wait_for_export(qapp, page.export_screen)
    assert not page.export_screen.queued
    assert len(list(tmp_path.glob("*.svg"))) == 4


@pytest.mark.uitest
def test_inline_result_and_check_before_you_print(stage, qapp, tmp_path):
    page, _shell = stage
    workflow_settings.set_export_folder(tmp_path)
    screen = page.export_screen
    with patch("joystick_diagrams.ui.export_page.QMessageBox.exec") as modal:
        page.export()
        wait_for_export(qapp, screen)
    modal.assert_not_called()  # no Confirm, no Completed
    assert screen.last_result_text == f"4 diagrams saved to {tmp_path}"
    assert screen.result_frame.isVisibleTo(screen)
    assert screen.last_notice_lines[0] == (
        "Gladiator NXT: 1 binding won't show because the template has no box "
        "for Button 99."
    )
    assert screen.notices_frame.isVisibleTo(screen)
    status = page.stage_status()
    assert status.icon == "ok" and status.text.startswith("Exported 4 at ")
    screen.dismiss_result()
    assert not screen.result_frame.isVisibleTo(screen)


@pytest.mark.uitest
def test_unwritable_folder_needs_a_decision(stage, qapp, tmp_path):
    page, _shell = stage
    workflow_settings.set_export_folder(tmp_path)
    with (
        patch(
            "joystick_diagrams.ui.export_page.folder_is_writable", return_value=False
        ),
        patch(
            "joystick_diagrams.ui.export_page.decision_dialog", return_value=False
        ) as decide,
    ):
        assert page.export_screen.start_export() is False
    decide.assert_called_once()
    assert decide.call_args.args[1] == S.CANT_WRITE_TITLE.format(folder=tmp_path)


@pytest.mark.uitest
def test_status_while_exporting_and_without_templates(qapp, settings_store):
    seed_state(templates={})
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    status = page.stage_status()
    assert (status.icon, status.text) == ("none", S.STATUS_CHOOSE_TEMPLATES)
    assert not page.next_action().enabled
    screen = page.export_screen
    screen._busy, screen._progress = True, (12, 33)
    assert page.stage_status().text == "Exporting 12 of 33…"
    assert page.stage_status().icon == "busy"
    screen._busy = False


@pytest.mark.uitest
def test_pdf_targets_are_queued_for_conversion(qapp, settings_store, tmp_path):
    from joystick_diagrams.ui.export_page import ExportDispatch, ExportJob

    seed_state()
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    devices = page.export_screen.export_list.selected_export_devices()
    job = ExportJob(devices[:1], [], devices, Path(tmp_path), "PDF")
    worker = ExportDispatch(job)
    outcomes = []
    worker.signals.finished.connect(outcomes.append)
    worker.run()
    qapp.processEvents()
    ((svg, target),) = outcomes[0].conversions
    assert target.endswith(".pdf") and Path(svg).with_suffix(".pdf") == Path(target)
    assert outcomes[0].results[0].export_format == "PDF"


@pytest.mark.uitest
def test_model_is_pure(qapp, settings_store):
    from joystick_diagrams.device_status import all_device_statuses
    from joystick_diagrams.ui.device_setup_controller import get_export_devices

    state = seed_state()
    statuses = all_device_statuses(state.profile_wrappers, include_unseen=False)
    model = build_export_model(get_export_devices(), statuses)
    assert sorted(model.default_ticks().values()) == [True, True, True, True]
    assert model.games == ["DCS World"]


@pytest.mark.uitest
def test_not_included_strip_is_rebuilt_not_repeated(stage):
    page, _shell = stage
    screen = page.export_screen
    for _ in range(3):
        screen.refresh()
    rows = [
        screen.not_included_box.itemAt(i).widget()
        for i in range(screen.not_included_box.count())
    ]
    assert len(rows) == 1 and all(r is not None for r in rows)


@pytest.mark.uitest
def test_first_launch_status_says_nothing_to_export(qapp, settings_store):
    seed_state(templates={}, profiles={})
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    status = page.stage_status()
    assert (status.icon, status.text) == ("none", S.STATUS_NOTHING_TO_EXPORT)


@pytest.mark.uitest
def test_choose_template_uses_the_picker_dialog(stage, monkeypatch):
    from joystick_diagrams.ui import export_page, template_picker

    page, _shell = stage
    made = {}

    class FakePicker:
        def __init__(self, device_guid, export_devices, parent, *, device_name=None):
            made.update(guid=device_guid, name=device_name, devices=export_devices)

        def exec(self):
            from joystick_diagrams.app_state import AppState
            from tests.ui.stage34_fixtures import STARTER_TEMPLATE

            AppState().device_service.set_template(made["guid"], str(STARTER_TEMPLATE))
            return export_page.QDialog.DialogCode.Accepted

    monkeypatch.setattr(template_picker, "TemplatePickerDialog", FakePicker)
    assert page.export_screen.choose_template(PANEL, "Button Box")
    assert made["guid"] == PANEL and made["name"] == "Button Box"
    assert [d.device_id for d in made["devices"]] == [PANEL, PANEL]
    row = page.export_screen.model.row(controller_key(PANEL))
    assert row is not None  # joins the list, ticked
    assert all(
        p.tick_key in page.export_screen.export_list.ticked_keys() for p in row.profiles
    )
