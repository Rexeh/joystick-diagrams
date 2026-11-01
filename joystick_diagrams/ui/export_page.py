"""4. Diagrams › Export (journey boards J08, J09, J13, J14 #5–#7).

The landing screen of stage 4: every ready profile ticked (remembered), the
"Not included" and "No diagram" lines, "Combine onto one page…", the tick
shortcuts and the settings rows (Format, Style, Save to, Also send to).

There is no Export button here and no Confirm or Completed dialog: the shell's
footer runs ``start_export()`` ("Export N diagrams"); progress goes to the status
bar ("Exporting 12 of 33…"); the result is one inline line, "33 diagrams saved
to <folder> [Open folder] ✕", plus a "Check before you print" block when some
bindings won't show or a style or layout couldn't be applied. A dialog opens
only when export can't go on without a choice: the first export (no folder
yet: the system folder dialog, pre-filled), a remembered folder that has gone,
a folder that can't be written to, a full disk.

While the shell reads the games (``read_in_progress``), the footer says "Export
when reading finishes"; pressing it queues the export, which starts by itself
on ``read_finished``.

Combined pages are exported in the same worker (``export.export_page`` for each
of ``export.page_profiles``); PNG and PDF are made afterwards on the UI thread
by ``PngConverter`` (``.pdf`` targets print at the page's real size). Every
file written, controller diagram or page, gets an ``ExportResult`` and the
batch goes to the other apps after conversion (pages: ``kind="page"``).
"""

from __future__ import annotations

import errno
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import qtawesome as qta
from PySide6.QtCore import (
    QObject,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import workflow_settings
from joystick_diagrams.app_state import AppState
from joystick_diagrams.export import (
    ExportDestination,
    export_page,
    export_with_report,
    page_member_devices,
    page_profiles,
)
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.modifier_identity import ModifierDisplay
from joystick_diagrams.plugins.output_plugin_interface import (
    KIND_PAGE,
    ExportResult,
)
from joystick_diagrams.render import RenderContext, build_render_context
from joystick_diagrams.ui import strings_diagrams as S
from joystick_diagrams.ui.device_setup import (
    ExportList,
    ExportModel,
    build_export_model,
    last_export_keys,
    page_key,
    store_last_export_keys,
)
from joystick_diagrams.ui.export_settings import (
    ExportSettings,
    ask_for_folder,
    link_button,
    suggested_export_folder,
)
from joystick_diagrams.ui.export_summary import (
    ExportSummary,
    check_notices,
    entry_for,
    gap_notice,
    result_line,
    styled_context,
)
from joystick_diagrams.ui.shell_access import find_shell, set_status_text
from joystick_diagrams.ui.stage_contract import (
    PAYLOAD_DEVICE_GUID,
    STAGE_CONTROLLERS,
)

_logger = logging.getLogger(__name__)

MUTED_STYLE = "color: #9AA0A6;"
NOTICE_FRAME_STYLE = (
    "QFrame#check_notices { background: rgba(245, 158, 11, 0.08); "
    "border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 6px; } "
    "QFrame#check_notices QWidget { background: transparent; }"
)
RESULT_FRAME_STYLE = (
    "QFrame#export_result { background: rgba(52, 211, 153, 0.08); "
    "border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 6px; } "
    "QFrame#export_result QLabel { background: transparent; }"
)


# ── Helpers ──


def read_time_text(stamp: str | None, now: datetime | None = None) -> str | None:
    """ "09:41" for today, "12 Oct" for an earlier day (local time)."""
    if not stamp:
        return None
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if when.tzinfo is not None:
        when = when.astimezone()
    now = now or datetime.now(when.tzinfo)
    if when.date() == now.date():
        return when.strftime("%H:%M")
    return f"{when.day} {when.strftime('%b')}"


def folder_is_writable(folder: Path) -> bool:
    return folder.is_dir() and os.access(folder, os.W_OK)


def choose_template_for(
    parent: QWidget | None,
    guid: str,
    name: str,
    export_devices: list[Any] | None = None,
) -> bool:
    """Open the template picker in place for one controller; True when one was chosen.

    Uses stage 2's ``TemplatePickerDialog`` (which stores the choice itself), else
    the file picker (``pick_template``, stored here).
    """
    state = AppState()
    service = state.device_service
    before = service.template(guid)
    from joystick_diagrams.ui import template_picker

    dialog_class = getattr(template_picker, "TemplatePickerDialog", None)
    if dialog_class is not None:
        if export_devices is None:
            try:
                from joystick_diagrams.ui.device_setup_controller import (
                    get_export_devices,
                )

                export_devices = [
                    d for d in get_export_devices() if d.device_id == guid
                ]
            except Exception:  # noqa: BLE001
                export_devices = []
        dialog = dialog_class(guid, export_devices, parent, device_name=name)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        after = service.template(guid)
        if after is not None and after != before:
            return True
        chosen = getattr(dialog, "chosen_path", None)
        chosen = chosen() if callable(chosen) else chosen
        if chosen:
            service.set_template(guid, str(chosen))
            return True
        return False
    path = template_picker.pick_template(parent, S.CHOOSE_TEMPLATE.rstrip("…"))
    if path is None:
        return False
    service.set_template(guid, str(path))
    return True


# ── Worker ──


@dataclass
class ExportJob:
    devices: list[Any]
    pages: list[tuple[Any, Any]]  # (Page, profile wrapper)
    all_devices: list[Any]
    folder: Path
    export_format: str
    ctx: RenderContext | None = None

    @property
    def total(self) -> int:
        return len(self.devices) + len(self.pages)


@dataclass
class ExportOutcome:
    summary: ExportSummary
    conversions: list[tuple[str, str]] = field(default_factory=list)
    results: list[ExportResult] = field(default_factory=list)
    locked: list[tuple[str, Any]] = field(default_factory=list)  # (name, job item)
    stopped: str | None = None  # "permission" | "disk_full"
    stop_detail: str = ""
    saved_keys: list[str] = field(default_factory=list)


class ExportSignals(QObject):
    progress = Signal(int, int)  # done, total
    finished = Signal(object)  # ExportOutcome


class ExportDispatch(QRunnable):
    """Writes every ticked diagram and page; conversions run afterwards on the UI thread."""

    def __init__(self, job: ExportJob):
        super().__init__()
        self.job = job
        self.signals = ExportSignals()

    @Slot()
    def run(self) -> None:
        job = self.job
        fmt = job.export_format.upper()
        summary = ExportSummary(
            styled=styled_context(job.ctx),
            modifiers_listed=job.ctx is not None
            and job.ctx.modifier_display is not ModifierDisplay.TEMPLATE_BOXES,
            total=job.total,
        )
        outcome = ExportOutcome(summary)
        done = 0
        items: list[tuple[str, Any]] = [("device", d) for d in job.devices] + [
            ("page", p) for p in job.pages
        ]
        for kind, item in items:
            try:
                if kind == "device":
                    self._export_device(item, fmt, outcome)
                else:
                    self._export_page(item, fmt, outcome)
                summary.count += 1
            except PermissionError as error:
                _logger.error(f"Couldn't write {self._name(kind, item)}: {error}")
                outcome.locked.append((self._name(kind, item), (kind, item)))
            except OSError as error:
                if error.errno == errno.ENOSPC:
                    outcome.stopped = "disk_full"
                    outcome.stop_detail = str(error)
                    break
                _logger.error(f"Couldn't export {self._name(kind, item)}: {error}")
                summary.failed += 1
            except Exception as error:  # noqa: BLE001 - one diagram never stops the batch
                _logger.error(
                    f"Couldn't export {self._name(kind, item)}: {error}", exc_info=True
                )
                summary.failed += 1
            done += 1
            self.signals.progress.emit(done, job.total)
        if outcome.locked and summary.count == 0 and not outcome.stopped:
            outcome.stopped = "permission"
            outcome.stop_detail = str(job.folder)
        self._call_plugin_exports()
        self.signals.finished.emit(outcome)

    @staticmethod
    def _name(kind: str, item: Any) -> str:
        if kind == "device":
            return f"{item.device_name} · {item.profile_wrapper.profile_name}"
        page, wrapper = item
        return f"{page.name} · {wrapper.profile_name}"

    def _export_device(self, item: Any, fmt: str, outcome: ExportOutcome) -> None:
        job = self.job
        output = export_with_report(
            item, str(job.folder), "PNG" if fmt == "PNG" else "SVG", ctx=job.ctx
        )
        if output is None:
            raise RuntimeError(f"{item.device_name} has no template")
        outcome.summary.entries.append(entry_for(item, output.report))
        svg_path = output.svg_path
        target = output.png_path
        if fmt == "PDF":
            target = str(Path(svg_path).with_suffix(".pdf"))
        if target:
            outcome.conversions.append((svg_path, target))
        outcome.results.append(
            ExportResult(
                profile_name=item.profile_wrapper.profile_name,
                device_name=item.device_name,
                device_guid=item.device_id,
                source_plugin=item.profile_wrapper.profile_origin.name,
                template_name=item.template_file_name,
                export_format=fmt,
                file_path=Path(target or svg_path),
                export_directory=Path(job.folder),
                device=item.device,
            )
        )

    def _export_page(self, item: tuple[Any, Any], fmt: str, outcome: ExportOutcome):
        job = self.job
        page, wrapper = item
        output = export_page(
            page,
            wrapper,
            job.all_devices,
            job.ctx,
            ExportDestination(Path(job.folder), fmt),
        )
        if output.compose is not None:
            for warning in output.compose.warnings:
                outcome.summary.page_warnings.append(f"{page.name}: {warning}")
        if output.conversion_target:
            outcome.conversions.append((output.svg_path, output.conversion_target))
        devices = page_member_devices(page, wrapper, job.all_devices)
        if not devices:
            return
        outcome.results.append(
            ExportResult(
                profile_name=wrapper.profile_name,
                device_name=page.name,
                device_guid=page.page_id,
                source_plugin=wrapper.profile_origin.name,
                template_name=None,
                export_format=fmt,
                file_path=Path(output.conversion_target or output.svg_path),
                export_directory=Path(job.folder),
                device=devices[0],
                kind=KIND_PAGE,
                page_name=page.name,
                devices=devices,
            )
        )

    def _call_plugin_exports(self) -> None:
        """Games that export their own files (``export_mappings``) get the folder too."""
        try:
            manager = AppState().plugin_manager
            wrappers = manager.get_enabled_plugin_wrappers() if manager else []
        except Exception as error:  # noqa: BLE001
            _logger.debug(f"No game exports: {error}")
            return
        for wrapper in wrappers:
            plugin = getattr(wrapper, "plugin", None)
            if plugin is None or not hasattr(plugin, "export_mappings"):
                continue
            try:
                plugin.export_mappings(Path(self.job.folder))
            except Exception as error:  # noqa: BLE001
                _logger.error(f"Export for {wrapper.name} failed: {error}")


class OutputPluginSignals(QObject):
    finished = Signal()


class OutputPluginDispatch(QRunnable):
    """Sends the exported files to the other apps (output plugins)."""

    def __init__(self, results: list):
        super().__init__()
        self.results = results
        self.signals = OutputPluginSignals()

    @Slot()
    def run(self):
        manager = AppState().output_plugin_manager
        if manager:
            for wrapper in manager.get_enabled_plugin_wrappers():
                try:
                    wrapper.run(self.results)
                except Exception as e:  # noqa: BLE001
                    _logger.error(
                        f"Output plugin '{wrapper.name}' raised an exception: {e}"
                    )
        self.signals.finished.emit()


# ── Dialogs that need a decision ──


class FolderGoneDialog(QDialog):
    """J14 #6: the remembered folder is unavailable; asked again, pre-filled."""

    def __init__(self, previous: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(S.FOLDER_GONE_TITLE.format(folder=previous))
        layout = QVBoxLayout(self)
        title = QLabel(S.FOLDER_GONE_TITLE.format(folder=previous))
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        text = QLabel(S.FOLDER_GONE_TEXT)
        text.setWordWrap(True)
        layout.addWidget(text)
        row = QHBoxLayout()
        self.path_edit = QLineEdit(previous)
        self.path_edit.setAccessibleName(S.SAVE_TO)
        row.addWidget(self.path_edit, 1)
        browse = QPushButton(S.CHOOSE_FOLDER)
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        layout.addLayout(row)
        buttons = QDialogButtonBox()
        buttons.addButton(S.CANCEL, QDialogButtonBox.ButtonRole.RejectRole)
        self.export_here = buttons.addButton(
            S.EXPORT_HERE, QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(520, 0)

    def _browse(self) -> None:
        start = Path(self.path_edit.text() or str(suggested_export_folder()))
        chosen = ask_for_folder(self, start)
        if chosen is not None:
            self.path_edit.setText(str(chosen))

    def folder(self) -> Path | None:
        text = self.path_edit.text().strip()
        return Path(text) if text else None


def ask_again_for_folder(parent: QWidget | None, previous: str) -> Path | None:
    """The folder-gone dialog; the folder to export to (created if needed) or None."""
    dialog = FolderGoneDialog(previous, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    folder = dialog.folder()
    if folder is None:
        return None
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        _logger.warning(f"Couldn't create {folder}: {error}")
        return folder  # the writable check that follows explains it
    workflow_settings.set_export_folder(folder)
    return folder


def decision_dialog(
    parent: QWidget | None, title: str, text: str, detail: str = ""
) -> bool:
    """An error that needs a choice: [Choose folder…] [Cancel]. True to choose again."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(title)
    box.setInformativeText(text)
    if detail:
        box.setDetailedText(detail)
    choose = box.addButton(S.CHOOSE_FOLDER, QMessageBox.ButtonRole.AcceptRole)
    box.addButton(S.CANCEL, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(choose)
    box.exec()
    return box.clickedButton() is choose


# ── Screen ──


class ExportScreen(QWidget):
    """The Export sub-screen of 4. Diagrams."""

    request_stage = Signal(int, dict)
    state_changed = Signal()  # count, busy or queued changed: refresh strip + footer
    appearance_requested = Signal()
    layout_requested = Signal(str)  # controller guid
    page_layout_requested = Signal(str)  # page id
    combine_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self.threadPool = QThreadPool()
        self._export_devices: list[ExportDevice] = []
        self._statuses: dict = {}
        self.model = ExportModel()
        self._busy = False
        self._progress: tuple[int, int] = (0, 0)
        self._queued = False
        self._shell_hooked = False
        self._job: ExportJob | None = None
        self._outcome: ExportOutcome | None = None
        self._converter = None
        self._preview_window = None
        self._last_export: tuple[int, str] | None = None  # (count, "09:52")
        self._stopped_reason: str | None = None
        self._loaded = False
        self.last_result_text = ""
        self.last_notice_lines: list[str] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(8)

        heading = QLabel(S.NAV_EXPORT)
        heading.setObjectName("heading_label")
        root.addWidget(heading)
        intro_row = QHBoxLayout()
        self.intro = QLabel(S.EXPORT_INTRO)
        self.intro.setObjectName("device_help_label")
        intro_row.addWidget(self.intro, 1)
        self.read_label = QLabel()
        self.read_label.setStyleSheet(MUTED_STYLE)
        intro_row.addWidget(self.read_label)
        self.read_again_button = link_button(S.READ_AGAIN)
        self.read_again_button.clicked.connect(self._read_again)
        intro_row.addWidget(self.read_again_button)
        root.addLayout(intro_row)

        # Inline result + "Check before you print"
        self.result_frame = QFrame()
        self.result_frame.setObjectName("export_result")
        self.result_frame.setStyleSheet(RESULT_FRAME_STYLE)
        result_row = QHBoxLayout(self.result_frame)
        result_row.setContentsMargins(12, 6, 6, 6)
        result_row.setSpacing(8)
        self.result_icon = QLabel()
        self.result_icon.setPixmap(
            qta.icon("fa5s.check-circle", color="#34D399").pixmap(QSize(16, 16))
        )
        result_row.addWidget(self.result_icon)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        result_row.addWidget(self.result_label, 1)
        self.retry_button = QPushButton()
        self.retry_button.setProperty("class", "plugin-setup-button")
        self.retry_button.clicked.connect(self._retry_locked)
        result_row.addWidget(self.retry_button)
        self.show_which_button = link_button(S.SHOW_WHICH)
        self.show_which_button.clicked.connect(self._show_locked)
        result_row.addWidget(self.show_which_button)
        self.open_folder_button = QPushButton(S.OPEN_FOLDER)
        self.open_folder_button.setProperty("class", "plugin-setup-button")
        self.open_folder_button.setToolTip(S.OPEN_FOLDER_TIP)
        self.open_folder_button.clicked.connect(self.open_folder)
        result_row.addWidget(self.open_folder_button)
        dismiss = QPushButton()
        dismiss.setIcon(qta.icon("fa5s.times", color="#9AA0A6"))
        dismiss.setFlat(True)
        dismiss.setToolTip(S.DISMISS_TIP)
        dismiss.setAccessibleName(S.DISMISS)
        dismiss.setProperty("class", "guidance-banner-close")
        dismiss.clicked.connect(self.dismiss_result)
        result_row.addWidget(dismiss)
        self.result_frame.hide()
        root.addWidget(self.result_frame)

        self.notices_frame = QFrame()
        self.notices_frame.setObjectName("check_notices")
        self.notices_frame.setStyleSheet(NOTICE_FRAME_STYLE)
        self.notices_layout = QVBoxLayout(self.notices_frame)
        self.notices_layout.setContentsMargins(12, 8, 12, 8)
        self.notices_layout.setSpacing(6)
        self.notices_frame.hide()
        root.addWidget(self.notices_frame)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.game_filter = QComboBox()
        self.game_filter.setProperty("class", "view-binds-list")
        self.game_filter.setAccessibleName(S.GAME_FILTER_ALL)
        self.game_filter.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.game_filter)
        self.search = QLineEdit()
        self.search.setPlaceholderText(S.PROFILE_SEARCH)
        self.search.setAccessibleName(S.PROFILE_SEARCH)
        self.search.setClearButtonEnabled(True)
        self.search.setProperty("class", "binds-search")
        self.search.addAction(
            qta.icon("fa5s.search", color="#9AA0A6"),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search, 1)
        root.addLayout(filter_row)

        # The list
        self.export_list = ExportList()
        self.export_list.setMinimumHeight(200)
        self.export_list.ticks_changed.connect(self._on_ticks_changed)
        self.export_list.why_requested.connect(self.show_why)
        self.export_list.preview_requested.connect(self.open_preview)
        self.export_list.edit_layout_requested.connect(self.layout_requested.emit)
        self.export_list.page_layout_requested.connect(self.page_layout_requested.emit)
        # Older callers know the tree as ``device_widget``
        self.device_widget = self.export_list

        # The list and its empty state share the stretching slot
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.addStretch(1)
        self.empty_label = QLabel(S.NOTHING_TO_EXPORT)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #9AA0A6; padding: 16px;")
        empty_layout.addWidget(self.empty_label)
        self.go_to_controllers_button = QPushButton(S.GO_TO_CONTROLLERS)
        self.go_to_controllers_button.setProperty("class", "plugin-setup-button")
        self.go_to_controllers_button.clicked.connect(
            lambda: self.request_stage.emit(STAGE_CONTROLLERS, {})
        )
        empty_layout.addWidget(
            self.go_to_controllers_button, alignment=Qt.AlignmentFlag.AlignCenter
        )
        empty_layout.addStretch(2)
        self.list_stack = QStackedWidget()
        self.list_stack.addWidget(self.export_list)
        self.list_stack.addWidget(self.empty_state)
        root.addWidget(self.list_stack, 1)

        # Not included · No diagram
        self.not_included_box = QVBoxLayout()
        self.not_included_box.setSpacing(2)
        root.addLayout(self.not_included_box)
        no_diagram_row = QHBoxLayout()
        no_diagram_row.setSpacing(4)
        self.no_diagram_label = QLabel()
        self.no_diagram_label.setStyleSheet(MUTED_STYLE)
        self.no_diagram_label.setWordWrap(True)
        no_diagram_row.addWidget(self.no_diagram_label, 1)
        self.no_diagram_change = link_button(S.CHANGE)
        self.no_diagram_change.clicked.connect(self._change_no_diagram)
        no_diagram_row.addWidget(self.no_diagram_change)
        root.addLayout(no_diagram_row)

        # Combine · Tick: All · None · Same as last export
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)
        self.combine_button = QPushButton(S.COMBINE)
        self.combine_button.setIcon(qta.icon("fa5s.object-group", color="white"))
        self.combine_button.setProperty("class", "plugin-setup-button")
        self.combine_button.clicked.connect(self.combine_requested.emit)
        actions_row.addWidget(self.combine_button)
        actions_row.addStretch(1)
        tick_label = QLabel(S.TICK)
        tick_label.setStyleSheet(MUTED_STYLE)
        actions_row.addWidget(tick_label)
        self.tick_all_button = link_button(S.TICK_ALL)
        self.tick_all_button.clicked.connect(self.export_list.tick_all)
        actions_row.addWidget(self.tick_all_button)
        actions_row.addWidget(QLabel("·"))
        self.tick_none_button = link_button(S.TICK_NONE)
        self.tick_none_button.clicked.connect(self.export_list.tick_none)
        actions_row.addWidget(self.tick_none_button)
        actions_row.addWidget(QLabel("·"))
        self.tick_last_button = link_button(S.TICK_LAST)
        self.tick_last_button.clicked.connect(self.export_list.tick_same_as_last)
        actions_row.addWidget(self.tick_last_button)
        root.addLayout(actions_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(separator)
        self.export_settings_widget = ExportSettings()
        self.export_settings_widget.style_change_requested.connect(
            self.appearance_requested.emit
        )
        self.export_settings_widget.other_apps_requested.connect(self._open_other_apps)
        self.export_settings_widget.format_changed.connect(
            lambda _fmt: self.state_changed.emit()
        )
        root.addWidget(self.export_settings_widget)

    # ── Data ──

    def _load_data(self) -> None:
        wrappers = list(self.appState.profile_wrappers)
        try:
            from joystick_diagrams.ui.device_setup_controller import get_export_devices

            self._export_devices = get_export_devices()
        except Exception as error:  # noqa: BLE001 - never let the screen fail to open
            _logger.warning(f"Could not load controllers for export: {error}")
            self._export_devices = []
        try:
            from joystick_diagrams.device_status import all_device_statuses

            self._statuses = all_device_statuses(wrappers, include_unseen=False)
        except Exception as error:  # noqa: BLE001
            _logger.warning(f"Could not work out controller statuses: {error}")
            self._statuses = {}

    @property
    def loaded(self) -> bool:
        return self._loaded

    def refresh(self) -> None:
        if self._busy:
            return  # ticks are locked while exporting; refreshed when it ends
        self._loaded = True
        self._load_data()
        try:
            pages = self.appState.page_service.pages()
        except Exception as error:  # noqa: BLE001
            _logger.warning(f"Could not load pages: {error}")
            pages = []
        self.model = build_export_model(
            self._export_devices, self._statuses, pages, page_profiles
        )
        self.export_list.set_model(self.model)
        self._reload_games()
        self._rebuild_not_included()
        has_rows = bool(self.model.rows)
        self.list_stack.setCurrentWidget(
            self.export_list if has_rows else self.empty_state
        )
        ready = [r for r in self.model.rows if r.kind == "controller"]
        self.combine_button.setEnabled(len(ready) >= 2)
        self.export_settings_widget.refresh()
        self._update_read_line()
        self.state_changed.emit()

    def _reload_games(self) -> None:
        current = self.game_filter.currentData()
        self.game_filter.blockSignals(True)
        self.game_filter.clear()
        self.game_filter.addItem(S.GAME_FILTER_ALL, "")
        for game in self.model.games:
            self.game_filter.addItem(game, game)
        index = self.game_filter.findData(current) if current else 0
        self.game_filter.setCurrentIndex(max(index, 0))
        self.game_filter.blockSignals(False)
        self.game_filter.setVisible(len(self.model.games) > 1)
        self._apply_filter()

    def _apply_filter(self) -> None:
        self.export_list.set_filter(
            self.game_filter.currentData() or "", self.search.text()
        )

    def _clear_layout(self, layout) -> None:
        """Remove every row now (hidden and detached at once, deleted later)."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())
                item.layout().deleteLater()

    def _rebuild_not_included(self) -> None:
        self._clear_layout(self.not_included_box)
        for entry in self.model.not_included:
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            icon = QLabel()
            icon.setPixmap(
                qta.icon("fa5s.exclamation-triangle", color="#F59E0B").pixmap(
                    QSize(12, 12)
                )
            )
            row.addWidget(icon)
            label = QLabel(entry.text)
            label.setStyleSheet("color: #E8EAED;")
            row.addWidget(label)
            row.addWidget(QLabel("·"))
            button = link_button(S.CHOOSE_TEMPLATE)
            button.setAccessibleName(f"{S.CHOOSE_TEMPLATE} {entry.name}")
            button.clicked.connect(
                lambda _c=False, g=entry.guid, n=entry.name: self.choose_template(g, n)
            )
            row.addWidget(button)
            row.addStretch(1)
            self.not_included_box.addWidget(row_widget)
        if self.model.no_diagram:
            items = ", ".join(
                S.NO_DIAGRAM_ITEM.format(controller=name, reason=reason)
                if reason
                else name
                for _guid, name, reason in self.model.no_diagram
            )
            self.no_diagram_label.setText(S.NO_DIAGRAM_LINE.format(items=items) + " ·")
            self.no_diagram_label.show()
            self.no_diagram_change.show()
        else:
            self.no_diagram_label.hide()
            self.no_diagram_change.hide()

    def _update_read_line(self) -> None:
        stamp = None
        inventory = getattr(self.appState, "device_inventory_service", None)
        if inventory is not None:
            try:
                stamp = inventory.latest_read()
            except Exception:  # noqa: BLE001
                stamp = None
        time = read_time_text(stamp)
        reading = self.read_in_progress()
        if time is None:
            text = S.BINDINGS_NOT_READ
        elif reading:
            text = S.BINDINGS_READ_NOW.format(time=time)
        else:
            text = S.BINDINGS_READ.format(time=time) + " ·"
        self.read_label.setText(text)
        shell = find_shell(self)
        self.read_again_button.setVisible(
            not reading and shell is not None and hasattr(shell, "start_read")
        )
        self._update_empty_state(reading)

    def _update_empty_state(self, reading: bool | None = None) -> None:
        """While the launch read runs there are no bindings yet: say so instead of
        sending the player to 2. Controllers."""
        reading = self.read_in_progress() if reading is None else reading
        waiting_for_read = reading and not self.model.rows
        self.empty_label.setText(
            S.WAITING_FOR_READ if waiting_for_read else S.NOTHING_TO_EXPORT
        )
        self.go_to_controllers_button.setVisible(not waiting_for_read)
        self.intro.setVisible(bool(self.model.rows))

    # ── Counts and state (for the shell) ──

    def export_count(self) -> int:
        return self.export_list.ticked_count()

    @property
    def is_exporting(self) -> bool:
        return self._busy

    @property
    def progress(self) -> tuple[int, int]:
        return self._progress

    @property
    def queued(self) -> bool:
        return self._queued

    @property
    def last_export(self) -> tuple[int, str] | None:
        return self._last_export

    @property
    def stopped_reason(self) -> str | None:
        return self._stopped_reason

    def read_in_progress(self) -> bool:
        shell = find_shell(self)
        return bool(getattr(shell, "read_in_progress", False)) if shell else False

    def can_queue(self) -> bool:
        """Export can wait for the read: something is ticked, or (on a launch
        read, before any bindings are in) there was an export last time."""
        return bool(self.export_count() or last_export_keys())

    def ready_count(self) -> int:
        return len(self.model.rows)

    def waiting_count(self) -> int:
        """Controllers (or pages) that would export once they have a template."""
        return len(self.model.not_included)

    def _on_ticks_changed(self, _count: int) -> None:
        self.state_changed.emit()

    # ── Navigation helpers ──

    def _read_again(self) -> None:
        shell = find_shell(self)
        start = getattr(shell, "start_read", None)
        if callable(start):
            start()
            self._update_read_line()

    def _change_no_diagram(self) -> None:
        payload = {}
        if self.model.no_diagram:
            payload[PAYLOAD_DEVICE_GUID] = self.model.no_diagram[0][0]
        self.request_stage.emit(STAGE_CONTROLLERS, payload)

    def _open_other_apps(self) -> None:
        shell = find_shell(self)
        opener = getattr(shell, "load_settings_page", None)
        if callable(opener):
            opener()

    def choose_template(self, guid: str, name: str) -> bool:
        """ "Choose template…" in place; on success the controller joins the list, ticked."""
        if not choose_template_for(self, guid, name):
            return False
        self.refresh()
        self.export_list.tick_row(f"device:{guid}", True)
        shell = find_shell(self)
        refresh_strip = getattr(shell, "refresh_strip", None)
        if callable(refresh_strip):
            refresh_strip()
        return True

    def tick_page(self, page_id: str) -> None:
        self.export_list.tick_row(page_key(page_id), True)

    def show_why(self, guid: str) -> None:
        """Why? — the plain-words list of controls without a box, with the two fixes."""
        info = self._statuses.get(guid)
        if info is None:
            return
        name = info.name or guid
        box = QMessageBox(self)
        box.setWindowTitle(S.WHY_TITLE.format(controller=name))
        box.setText(gap_notice(name, list(info.missing_controls)))
        layout_button = box.addButton(
            S.NOTICE_GAPS_ACTION_LAYOUT, QMessageBox.ButtonRole.ActionRole
        )
        template_button = box.addButton(
            S.WHY_CHOOSE_ANOTHER, QMessageBox.ButtonRole.ActionRole
        )
        box.addButton(S.WHY_CLOSE, QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is layout_button:
            self.layout_requested.emit(guid)
        elif clicked is template_button:
            self.choose_template(guid, name)

    def open_preview(self, export_device: ExportDevice):
        """The read-only Preview window for one controller."""
        from joystick_diagrams.ui.preview_window import PreviewWindow

        siblings = self.export_list.export_devices_for(export_device.device_id) or [
            export_device
        ]
        if self._preview_window is not None:
            self._preview_window.close()
        self._preview_window = PreviewWindow(siblings, export_device, self)
        self._preview_window.edit_layout_requested.connect(self.layout_requested.emit)
        self._preview_window.show()
        return self._preview_window

    def shutdown(self) -> None:
        if self._preview_window is not None:
            self._preview_window.close()
            self._preview_window = None

    # ── Export ──

    def start_export(self) -> bool:
        """The footer's "Export N diagrams". Queues while a read is in progress."""
        if self._busy:
            return False
        self.export_list.flush()
        if self.read_in_progress() and self.can_queue():
            self.queue_export()
            return False
        if self.export_count() == 0:
            return False
        folder = self.resolve_folder()
        if folder is None:
            return False
        devices = self.export_list.selected_export_devices()
        pages = self.export_list.selected_page_jobs()
        job = ExportJob(
            devices,
            pages,
            list(self._export_devices),
            folder,
            self.export_settings_widget.get_export_format(),
            ctx=build_render_context(),
        )
        self._run(job, self.export_list.ticked_keys())
        return True

    def queue_export(self) -> None:
        self._queued = True
        shell = find_shell(self)
        signal = getattr(shell, "read_finished", None)
        if signal is not None and not self._shell_hooked:
            try:
                signal.connect(self._on_shell_read_finished)
                self._shell_hooked = True
            except (TypeError, RuntimeError, AttributeError):
                pass
        self.state_changed.emit()

    def cancel_queued(self) -> None:
        self._queued = False
        self.state_changed.emit()

    def _on_shell_read_finished(self, *_args) -> None:
        if self._queued:
            QTimer.singleShot(0, self._run_queued)

    def on_read_started(self, *_args) -> None:
        self._update_read_line()
        self.state_changed.emit()

    def on_read_finished(self, *_args) -> None:
        self._on_shell_read_finished()
        self._update_read_line()

    def _run_queued(self) -> None:
        if not self._queued or self.read_in_progress():
            return
        self._queued = False
        self.refresh()
        self.start_export()
        self.state_changed.emit()

    def resolve_folder(self) -> Path | None:
        """The folder to export to: asks the first time, re-asks if it has gone."""
        folder = workflow_settings.get_export_folder()
        if folder is None:
            previous = workflow_settings.get_export_folder_raw()
            if previous:
                folder = ask_again_for_folder(self, previous)
            else:
                folder = ask_for_folder(self, suggested_export_folder())
            self.export_settings_widget.refresh_folder()
            if folder is None:
                return None
        while not folder_is_writable(folder):
            again = decision_dialog(
                self,
                S.CANT_WRITE_TITLE.format(folder=folder),
                S.CANT_WRITE_TEXT.format(saved=S.SAVED_SO_FAR_NONE),
            )
            if not again:
                return None
            folder = ask_for_folder(self, folder)
            self.export_settings_widget.refresh_folder()
            if folder is None:
                return None
        return folder

    def _run(self, job: ExportJob, ticked_keys: list[str]) -> None:
        self._busy = True
        self._stopped_reason = None
        self._job = job
        self._ticked_at_start = ticked_keys
        self._progress = (0, job.total)
        self.export_list.set_locked(True)
        self.export_settings_widget.set_locked(True)
        self.dismiss_result()
        set_status_text(self, S.STATUS_EXPORTING.format(done=0, total=job.total), 0)
        self.state_changed.emit()
        worker = ExportDispatch(job)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.finished.connect(self._on_written)
        self.threadPool.start(worker)

    def _on_progress(self, done: int, total: int) -> None:
        self._progress = (done, total)
        percent = round(done / total * 100) if total else 100
        set_status_text(
            self, S.STATUS_EXPORTING.format(done=done, total=total), percent
        )
        self.state_changed.emit()

    def _on_written(self, outcome: ExportOutcome) -> None:
        self._outcome = outcome
        if outcome.stopped:
            self._stop(outcome)
            return
        if outcome.conversions:
            self._convert(outcome)
        else:
            self._after_conversion()

    def _convert(self, outcome: ExportOutcome) -> None:
        from joystick_diagrams.export_image import PngConverter

        is_pdf = any(t.lower().endswith(".pdf") for _s, t in outcome.conversions)
        text = S.PROGRESS_MAKING_PDF if is_pdf else S.PROGRESS_MAKING_PNG
        set_status_text(self, text, 0)
        self._converter = PngConverter(list(outcome.conversions))
        self._converter.progress.connect(
            lambda current, total: set_status_text(
                self, text, round(current / total * 100) if total else 100
            )
        )
        self._converter.finished.connect(self._on_converted)
        self._converter.start()

    def _on_converted(self) -> None:
        if self._converter is not None:
            self._converter.deleteLater()
            self._converter = None
        self._after_conversion()

    def _after_conversion(self) -> None:
        outcome = self._outcome
        manager = getattr(self.appState, "output_plugin_manager", None)
        enabled = []
        if manager is not None:
            try:
                enabled = list(manager.get_enabled_plugin_wrappers())
            except Exception:  # noqa: BLE001
                enabled = []
        if outcome is not None and outcome.results and enabled:
            set_status_text(self, S.PROGRESS_OTHER_APPS, -1)
            dispatch = OutputPluginDispatch(outcome.results)
            dispatch.signals.finished.connect(self._finish)
            self.threadPool.start(dispatch)
        else:
            self._finish()

    def _unlock(self) -> None:
        self._busy = False
        self.export_list.set_locked(False)
        self.export_settings_widget.set_locked(False)

    def _finish(self) -> None:
        outcome = self._outcome
        job = self._job
        self._unlock()
        count = outcome.summary.count if outcome else 0
        set_status_text(
            self,
            S.STATUS_SAVED_AT.format(
                count=count, diagrams=S.plural(count, *S.DIAGRAMS), time=_now()
            ),
        )
        if outcome is not None and job is not None:
            store_last_export_keys(self._ticked_at_start)
            self._last_export = (outcome.summary.count, _now())
            self.show_result(outcome, job)
        self.state_changed.emit()

    def _stop(self, outcome: ExportOutcome) -> None:
        job = self._job
        self._unlock()
        reason = (
            S.STOP_REASON_DISK_FULL
            if outcome.stopped == "disk_full"
            else S.STOP_REASON_FOLDER
        )
        self._stopped_reason = reason
        set_status_text(self, S.STATUS_EXPORT_STOPPED.format(reason=reason))
        self.state_changed.emit()
        if job is None:
            return
        total = job.total
        saved = (
            S.SAVED_SO_FAR.format(
                count=outcome.summary.count,
                total=total,
                diagrams=S.plural(total, *S.DIAGRAMS),
            )
            if outcome.summary.count
            else S.SAVED_SO_FAR_NONE
        )
        if outcome.stopped == "disk_full":
            title, text = S.DISK_FULL_TITLE, S.DISK_FULL_TEXT
        else:
            title, text = S.CANT_WRITE_TITLE, S.CANT_WRITE_TEXT
        again = decision_dialog(
            self,
            title.format(folder=job.folder),
            text.format(saved=saved),
            outcome.stop_detail,
        )
        if again:
            folder = ask_for_folder(self, job.folder)
            self.export_settings_widget.refresh_folder()
            if folder is not None:
                self.start_export()

    # ── Result ──

    def show_result(self, outcome: ExportOutcome, job: ExportJob) -> None:
        summary = outcome.summary
        text = result_line(summary, str(job.folder))
        locked = len(outcome.locked)
        if locked:
            them = (
                S.RESULT_THOSE[0]
                if locked == 1
                else S.RESULT_THOSE[1].format(count=locked)
            )
            text = (
                S.RESULT_SAVED_PARTIAL.format(
                    count=summary.count,
                    total=job.total,
                    diagrams=S.plural(job.total, *S.DIAGRAMS),
                    folder=job.folder,
                )
                + " "
                + S.RESULT_LOCKED.format(count=locked, them=them)
            )
            self.retry_button.setText(
                S.TRY_THOSE_AGAIN[0]
                if locked == 1
                else S.TRY_THOSE_AGAIN[1].format(count=locked)
            )
        self.retry_button.setVisible(bool(locked))
        self.show_which_button.setVisible(bool(locked))
        icon = (
            "fa5s.check-circle"
            if not locked and not summary.failed
            else "fa5s.exclamation-triangle"
        )
        colour = "#34D399" if not locked and not summary.failed else "#F59E0B"
        self.result_icon.setPixmap(qta.icon(icon, color=colour).pixmap(QSize(16, 16)))
        self.result_label.setText(text)
        self.last_result_text = text
        self.result_frame.show()
        self._show_notices(summary, job)

    def _show_notices(self, summary: ExportSummary, job: ExportJob) -> None:
        self._clear_layout(self.notices_layout)
        lines: list[tuple[str, str | None]] = []
        exported_guids = list(dict.fromkeys(d.device_id for d in job.devices))
        for guid in exported_guids:
            info = self._statuses.get(guid)
            if info is not None and info.missing_controls:
                lines.append(
                    (gap_notice(info.name or guid, list(info.missing_controls)), guid)
                )
        lines.extend((line, None) for line in check_notices(summary))
        self.last_notice_lines = [line for line, _guid in lines]
        if not lines:
            self.notices_frame.hide()
            return
        title = QLabel(S.CHECK_BEFORE_PRINT)
        title.setStyleSheet("font-weight: bold; color: #F59E0B;")
        self.notices_layout.addWidget(title)
        for line, guid in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            self.notices_layout.addWidget(label)
            if guid is None:
                continue
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)
            add_boxes = link_button(S.NOTICE_GAPS_ACTION_LAYOUT)
            add_boxes.clicked.connect(
                lambda _c=False, g=guid: self.layout_requested.emit(g)
            )
            row.addWidget(add_boxes)
            other = link_button(S.NOTICE_GAPS_ACTION_TEMPLATE)
            info = self._statuses.get(guid)
            other.clicked.connect(
                lambda _c=False, g=guid, n=(info.name if info else guid): (
                    self.choose_template(g, n)
                )
            )
            row.addWidget(other)
            row.addStretch(1)
            self.notices_layout.addWidget(row_widget)
        self.notices_frame.show()

    def dismiss_result(self) -> None:
        self.result_frame.hide()
        self.notices_frame.hide()

    def open_folder(self) -> None:
        folder = self._job.folder if self._job is not None else None
        folder = folder or workflow_settings.get_export_folder()
        if folder is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _locked_items(self) -> list[tuple[str, Any]]:
        return list(self._outcome.locked) if self._outcome is not None else []

    def _show_locked(self) -> None:
        names = [name for name, _item in self._locked_items()]
        QMessageBox.information(self, S.SHOW_WHICH_TITLE, "\n".join(names))

    def _retry_locked(self) -> None:
        if self._busy or self._job is None:
            return
        items = [item for _name, item in self._locked_items()]
        devices = [i for kind, i in items if kind == "device"]
        pages = [i for kind, i in items if kind == "page"]
        if not devices and not pages:
            return
        job = ExportJob(
            devices,
            pages,
            self._job.all_devices,
            self._job.folder,
            self._job.export_format,
            ctx=build_render_context(),
        )
        self._run(job, self._ticked_at_start)


def _now() -> str:
    return datetime.now().strftime("%H:%M")


# The older name (the previous Export page)
ExportPage = ExportScreen


if __name__ == "__main__":
    pass
