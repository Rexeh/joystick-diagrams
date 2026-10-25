"""The four-stage acceptance walkthrough, end to end, with the real stylesheet.

docs/superpowers/plans/2026-10-25-four-stage-implementation.md › Acceptance:

1. Fresh data root with the DCS World game (the plugin from the sibling
   ``joystick-diagrams-dcs-world-plugin`` checkout, or ``JD_DCS_PLUGIN_DIR``)
   reading ``tests/data/sample_profiles/DCS``.
2. First launch lands on 1. Setup; choosing the folder reads it; the results
   card leads on with "Next: Choose 3 templates ›" to 2. Controllers, where the
   picker (fit counts on every row) assigns the real VKB, Warthog and Virpil
   templates; 3. Bindings; 4. Diagrams lands on Export with everything ticked.
3. The first export asks for a folder once (``QFileDialog`` patched), writes
   the files and shows the inline result; no modal dialog.
4. Relaunch: lands on the last stage, reads in the background, Export queues
   while reading and runs when the read finishes.
5. A page of two controllers exports one file per profile, with the dimmed
   panel ("No bindings in <profile>") where a member has no bindings; PNG and
   PDF too when QtWebEngine can start here.
6. Two controllers on the Starter Template keep independent layouts.

Set ``JD_WALKTHROUGH_SHOTS=<dir>`` to save screenshots of every step.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

import pytest  # noqa: E402
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DCS = REPO_ROOT / "tests" / "data" / "sample_profiles" / "DCS"
THEME_CSS = REPO_ROOT / "theme" / "custom.css"


def _dcs_plugin_dir() -> Path | None:
    candidates = [
        os.environ.get("JD_DCS_PLUGIN_DIR"),
        str(
            REPO_ROOT.parent / "joystick-diagrams-dcs-world-plugin" / "dcs_world_plugin"
        ),
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "main.py").is_file():
            return Path(candidate)
    return None


DCS_PLUGIN = _dcs_plugin_dir()

pytestmark = [
    pytest.mark.uitest,
    pytest.mark.skipif(
        DCS_PLUGIN is None,
        reason="the DCS World game checkout is not next to this repo",
    ),
]

STICK_NAME = "VKBsim Gladiator NXT R"
THROTTLE_NAME = "Throttle - HOTAS Warthog"
VIRPIL_NAME = "VPC Constellation ALPHA-R"
TEMPLATE_FOR = {
    STICK_NAME: "bundled:VKB Sim/VKB-Sim Gladiator NXT R.svg",
    THROTTLE_NAME: "bundled:Thrustmaster/Thrustmaster Warthog - Throttle.svg",
    VIRPIL_NAME: "bundled:Virpil/Virpil Constellation ALPHA R.svg",
}
PROFILES = {"f-16c_50", "fa-18c_hornet", "a-10c_2", "edge-cases"}  # casefolded


# ── Helpers ──


def pump(ms: int = 50) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def wait_until(predicate, timeout_ms: int = 60000) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if predicate():
            return True
        pump(25)
    return bool(predicate())


class Shots:
    """Saves ``window.grab()`` PNGs when ``JD_WALKTHROUGH_SHOTS`` is set."""

    def __init__(self) -> None:
        folder = os.environ.get("JD_WALKTHROUGH_SHOTS")
        self.folder = Path(folder) if folder else None
        if self.folder:
            self.folder.mkdir(parents=True, exist_ok=True)
        self.saved: list[Path] = []

    def __call__(self, widget: QWidget, name: str) -> None:
        if self.folder is None:
            return
        pump(150)
        path = self.folder / f"{name}.png"
        widget.grab().save(str(path))
        self.saved.append(path)


def _real_settings():
    """The root conftest makes ``get_setting`` return None; this walkthrough needs
    the real table so a relaunch remembers the last stage and the export folder."""
    from joystick_diagrams.db.db_connection import connection

    def get_setting(key: str) -> str | None:
        con = connection()
        row = con.execute(
            "SELECT value FROM settings WHERE setting_key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    return patch(
        "joystick_diagrams.db.db_settings.get_setting", side_effect=get_setting
    )


@pytest.fixture
def styled_app(qapp):
    """The app's own stylesheet (qt-material + theme/custom.css), restored after."""
    from qt_material import apply_stylesheet

    before_sheet, before_palette = qapp.styleSheet(), qapp.palette()
    apply_stylesheet(
        qapp,
        theme="dark_blue.xml",
        invert_secondary=False,
        extra={"font_family": "Roboto"},
        css_file=str(THEME_CSS),
    )
    yield qapp
    qapp.setStyleSheet(before_sheet)
    qapp.setPalette(before_palette)


def _start_app():
    """What ``app_init.init`` does after the database: managers, AppState."""
    from joystick_diagrams.app_state import AppState
    from joystick_diagrams.plugins.output_plugin_manager import OutputPluginManager
    from joystick_diagrams.plugins.plugin_manager import ParserPluginManager

    AppState._inst = None
    parsers = ParserPluginManager()
    parsers.load_discovered_plugins()
    parsers.create_plugin_wrappers()
    outputs = OutputPluginManager()
    outputs.load_discovered_plugins()
    outputs.create_plugin_wrappers()
    return AppState(plugin_manager=parsers, output_plugin_manager=outputs)


def _window(**kwargs):
    from joystick_diagrams.ui.main_window import MainWindow

    window = MainWindow(check_updates=False, **kwargs)
    window.resize(1280, 860)
    return window


def _guid_named(state, name: str) -> str:
    from joystick_diagrams.device_status import all_device_statuses

    for guid, info in all_device_statuses(state.profile_wrappers).items():
        if info.name == name:
            return guid
    raise AssertionError(f"{name} not found in the read")


class PickerDriver:
    """Stands in for the modal ``exec`` of the template picker: shows it, waits for
    the fit counts, chooses the template named in ``TEMPLATE_FOR``."""

    def __init__(self, shots: Shots):
        self.shots = shots
        self.opened: list[str] = []
        self.fit_texts: dict[str, list[str]] = {}

    def exec(self, dialog) -> int:
        dialog.show()
        assert dialog.wait_for_fits(60000), "fit counts never arrived"
        name = dialog.device_name
        self.opened.append(name)
        key = TEMPLATE_FOR[name]
        assert dialog.select_template(key), f"{key} is not in the picker"
        pump(300)  # the preview pane and thumbnail
        rows = dialog.template_items()
        self.fit_texts[name] = [row.text(1) for row in rows]
        if len(self.opened) == 1:
            self.shots(dialog, "04_template_picker")
        dialog._use_selected()
        dialog.hide()
        return dialog.result()


def _accept_pages_dialog(guids: list[str], shots: Shots):
    from joystick_diagrams.render.page import SizePreset

    def fake_exec(dialog) -> int:
        dialog.show()
        for guid in guids:
            dialog.member_boxes[guid].setChecked(True)
        # Make this page for: profiles with both controllers (the default)
        assert dialog.rule_shared.isChecked()
        assert dialog.rule_shared.text().endswith("· 1 profile"), (
            dialog.rule_shared.text()
        )
        assert "· 4 profiles" in dialog.rule_any.text()
        dialog._toggle_rule_list()
        dialog.name_edit.setText("Stick and throttle")
        index = dialog.size_combo.findData(SizePreset.A4.value)
        dialog.size_combo.setCurrentIndex(max(index, 0))
        pump(1500)  # live thumbnail
        shots(dialog, "10_pages_combine_dialog")
        dialog.accept()
        dialog.hide()
        return dialog.result()

    return fake_exec


def _no_modals():
    """Any QMessageBox during an export is a failure (results are inline)."""

    def fail(*_args, **_kwargs):
        raise AssertionError("a modal dialog was opened")

    return patch.object(QMessageBox, "exec", fail)


def _export_and_wait(screen, timeout_ms: int = 120000) -> None:
    assert wait_until(lambda: not screen.is_exporting, timeout_ms)


def _webengine_works() -> bool:
    if os.environ.get("JD_SKIP_WEBENGINE"):
        return False
    try:
        from PySide6.QtWebEngineCore import QWebEnginePage  # noqa: F401
    except ImportError:
        return False
    return True


# ── The walkthrough ──


def test_four_stage_walkthrough(styled_app, qtbot, tmp_path):  # noqa: PLR0915
    from joystick_diagrams import utils, workflow_settings
    from joystick_diagrams.device_status import DeviceStatus, all_device_statuses
    from joystick_diagrams.ui.stage_contract import (
        STAGE_BINDINGS,
        STAGE_CONTROLLERS,
        STAGE_DIAGRAMS,
        STAGE_SETUP,
    )
    from joystick_diagrams.ui.template_picker import TemplatePickerDialog

    shots = Shots()
    export_folder = tmp_path / "Kneeboards"
    export_folder.mkdir()

    # A fresh data root with DCS World added (as "Add a game from a file…" leaves it)
    shutil.copytree(
        DCS_PLUGIN,
        utils.user_parser_plugins_root() / "dcs_world_plugin",
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    with _real_settings():
        state = _start_app()
        dcs = next(
            w for w in state.plugin_manager.plugin_wrappers if w.name == "DCS World"
        )
        dcs.enabled = True

        # ── 1. Setup: first launch ──
        window = _window()
        qtbot.addWidget(window)
        window.show()
        assert window.current_stage == STAGE_SETUP
        setup = window.page(STAGE_SETUP)
        assert not window.read_in_progress  # nothing to read before a folder
        shots(window, "01_setup_first_launch")

        with qtbot.waitSignal(window.read_finished, timeout=60000):
            setup.use_path(dcs, SAMPLE_DCS)
        pump(200)
        results = setup.results_text()
        assert "We found 3 controllers in" in results, results
        action = window.footer.primary_button
        assert action.text() == "Next: Choose 3 templates ›"
        shots(window, "02_setup_results")

        # ── 2. Controllers ──
        action.click()
        assert window.current_stage == STAGE_CONTROLLERS
        controllers = window.page(STAGE_CONTROLLERS)
        assert window.footer.primary_button.text() == "Choose 3 templates"
        assert window.footer.secondary_button.text() == "Skip to 3. Bindings ›"
        shots(window, "03_controllers_needs_templates")

        driver = PickerDriver(shots)

        def picker_exec(dialog):  # a plain function, so it binds like a method
            return driver.exec(dialog)

        with patch.object(TemplatePickerDialog, "exec", picker_exec):
            for _ in range(3):
                window.footer.primary_button.click()  # "Choose N templates"
                pump(100)
        assert sorted(driver.opened) == sorted(TEMPLATE_FOR)
        for name, texts in driver.fit_texts.items():
            assert all(texts), f"a row without a fit count in {name}'s picker"
        statuses = all_device_statuses(state.profile_wrappers, include_unseen=False)
        assert {i.name for i in statuses.values() if i.state.exports} == set(
            TEMPLATE_FOR
        )
        assert controllers.stage_status().text == "All 3 ready"
        assert window.footer.primary_button.text() == "Next: 3. Bindings ›"
        shots(window, "05_controllers_all_ready")

        # ── 3. Bindings ──
        window.footer.primary_button.click()
        assert window.current_stage == STAGE_BINDINGS
        shots(window, "06_bindings")
        bindings = window.page(STAGE_BINDINGS)
        for section in ("shared", "labels"):
            bindings.show_section(section)
            shots(window, f"06_bindings_{section}")
        bindings.show_section("bindings")

        # ── 4. Diagrams: lands on Export, everything ticked ──
        window.go_to_stage(STAGE_DIAGRAMS)
        diagrams = window.page(STAGE_DIAGRAMS)
        screen = diagrams.export_screen
        assert diagrams.current_section() == "export"
        export_list = screen.export_list
        assert export_list.ticked_count() == len(screen.model.tick_keys) > 0
        export_label = window.footer.primary_button.text()
        assert export_label.startswith("Export ") and export_label.endswith(" diagrams")
        shots(window, "07_diagrams_export")

        # First export: asks for the folder once, writes, shows the result inline
        screen.export_settings_widget.set_export_format("SVG")
        with (
            patch(
                "joystick_diagrams.ui.export_settings.QFileDialog.getExistingDirectory",
                return_value=str(export_folder),
            ) as ask,
            _no_modals(),
        ):
            window.footer.primary_button.click()
            _export_and_wait(screen)
            assert ask.call_count == 1
            written = sorted(export_folder.glob("*.svg"))
            assert len(written) == screen.export_count() > 0
            assert screen.last_result_text.startswith(
                f"{len(written)} diagrams saved to"
            ), screen.last_result_text
            assert screen.result_frame.isVisible()
            shots(window, "08_export_result")

            # Second export never asks again
            window.footer.primary_button.click()
            _export_and_wait(screen)
            assert ask.call_count == 1
        assert workflow_settings.get_export_folder() == export_folder
        assert workflow_settings.get_last_stage() == STAGE_DIAGRAMS

        stick = _guid_named(state, STICK_NAME)
        throttle = _guid_named(state, THROTTLE_NAME)

        # ── Pages: two controllers, one file per profile, dimmed empty panel ──
        from joystick_diagrams.ui.pages_dialog import PagesDialog

        with patch.object(
            PagesDialog, "exec", _accept_pages_dialog([stick, throttle], shots)
        ):
            diagrams.combine()
        pages = state.page_service.pages()
        assert [p.name for p in pages] == ["Stick and throttle"]
        page_key = f"page:{pages[0].page_id}"
        assert any(k.startswith(page_key) for k in export_list.ticked_keys())
        shots(window, "11_diagrams_page_row")
        diagrams.show_section("pages")
        shots(window, "12_diagrams_pages")
        diagrams.show_section("appearance")
        shots(window, "12_diagrams_appearance")
        diagrams.show_section("export")

        page_folder = tmp_path / "Pages"
        page_folder.mkdir()
        workflow_settings.set_export_folder(page_folder)
        export_list.tick_none()
        screen.tick_page(pages[0].page_id)
        with _no_modals():
            window.footer.primary_button.click()
            _export_and_wait(screen)
        # Default rule: only the profile where both controllers have bindings
        shared_files = sorted(page_folder.glob("Stick and throttle - *.svg"))
        assert [p.stem.split(" - ", 1)[1].casefold() for p in shared_files] == [
            "f-16c_50"
        ]
        for old in shared_files:
            old.unlink()

        # "Any profile that uses one of them": every profile, empty panels dimmed
        from joystick_diagrams.render.page import ProfileRule

        state.page_service.save(
            pages[0].model_copy(update={"profile_rule": ProfileRule.ANY})
        )
        screen.refresh()
        export_list.tick_none()
        screen.tick_page(pages[0].page_id)
        with _no_modals():
            window.footer.primary_button.click()
            _export_and_wait(screen)
        page_files = sorted(page_folder.glob("Stick and throttle - *.svg"))
        assert {p.stem.split(" - ", 1)[1].casefold() for p in page_files} == PROFILES
        by_profile = {
            p.stem.split(" - ", 1)[1].casefold(): p.read_text(encoding="utf-8")
            for p in page_files
        }
        assert "No bindings in" in by_profile["a-10c_2"]  # the throttle, dimmed
        assert 'opacity="0.45"' in by_profile["a-10c_2"]
        assert "No bindings in" not in by_profile["f-16c_50"]  # both bound

        if _webengine_works():
            for fmt, suffix in (("PNG", ".png"), ("PDF", ".pdf")):
                screen.export_settings_widget.set_export_format(fmt)
                with _no_modals():
                    window.footer.primary_button.click()
                    _export_and_wait(screen, 240000)
                made = sorted(page_folder.glob(f"Stick and throttle - *{suffix}"))
                if not made:
                    pytest.skip(f"QtWebEngine couldn't make {fmt} files here")
                assert {p.stem.split(" - ", 1)[1].casefold() for p in made} == PROFILES
                assert all(p.stat().st_size > 1000 for p in made)

        # ── Layouts are per controller ──
        from joystick_diagrams.render.layout import MoveOp

        starter = REPO_ROOT / "templates" / "Starter Template.svg"
        virpil = _guid_named(state, VIRPIL_NAME)
        state.device_service.set_template(stick, str(starter))
        state.device_service.set_template(virpil, str(starter))
        key = "bundled:Starter Template.svg"
        from joystick_diagrams.render.layout import TEMPLATE_LAYER

        layouts = state.layout_service
        f16_key = next(
            w.profile_key
            for w in state.profile_wrappers
            if w.profile_name.casefold() == "f-16c_50"
        )
        layouts.append_op(
            key,
            TEMPLATE_LAYER,
            MoveOp(target="button_1", dx=40, dy=0),
            None,
            device_guid=stick,
        )
        assert layouts.get_layers(key, f16_key, stick).all_ops()
        assert not layouts.get_layers(key, f16_key, virpil).all_ops()
        diagrams.show_layout(stick)
        layout_screen = diagrams.layout_screen
        assert layout_screen.diagram_combo.currentData() == stick
        diagrams.show_layout(virpil)
        assert layout_screen.diagram_combo.currentData() == virpil
        shots(window, "13_diagrams_layout")
        window.close()
        diagrams.shutdown()

        # ── Relaunch: last stage, background read, Export queues while reading ──
        from joystick_diagrams.ui import stage_shell

        original_run = stage_shell.PluginExecutor.run

        def slow_run(executor):
            time.sleep(1.5)  # long enough to press Export while reading
            original_run(executor)

        state = _start_app()
        assert any(w.enabled for w in state.plugin_manager.plugin_wrappers)
        relaunch_folder = tmp_path / "Relaunch"
        relaunch_folder.mkdir()
        workflow_settings.set_export_folder(relaunch_folder)
        with patch.object(stage_shell.PluginExecutor, "run", slow_run):
            window = _window()
            qtbot.addWidget(window)
            assert window.current_stage == STAGE_DIAGRAMS
            window.show()
            assert wait_until(lambda: window.read_in_progress, 10000)
            screen = window.page(STAGE_DIAGRAMS).export_screen
            assert screen.read_in_progress()
            shots(window, "14_relaunch_reading")
            screen.export_settings_widget.set_export_format("SVG")
            assert window.footer.primary_button.text() == "Export when reading finishes"
            with _no_modals():
                window.footer.primary_button.click()
                assert screen.queued
                assert wait_until(lambda: not window.read_in_progress, 60000)
                assert wait_until(lambda: screen.last_result_text != "", 120000)
                _export_and_wait(screen)
        assert sorted(relaunch_folder.glob("*.svg"))
        assert not screen.queued
        shots(window, "15_relaunch_exported")

        window.load_settings_page()
        shots(window, "16_settings")
        window.go_to_stage(STAGE_SETUP)
        shots(window, "17_setup_returning")
        statuses = all_device_statuses(state.profile_wrappers, include_unseen=False)
        assert sum(1 for i in statuses.values() if i.state is DeviceStatus.READY) >= 1
        window.close()
        window.page(STAGE_DIAGRAMS).shutdown()

    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    QApplication.processEvents()
    assert QDialog is not None  # imported for the patches above
