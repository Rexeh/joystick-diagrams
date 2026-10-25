"""The template picker: ``TemplatePickerDialog(device_guid, export_devices)``.

Board J05. Search by template or maker; the bundled templates grouped by maker
plus **My templates**; a fit count on every template row ("Has all 31 controls
you use") from the controller's real bindings, computed lazily on a
``QThreadPool`` runnable and cached by ``template_catalog.fit``; a preview pane
(thumbnail rendered off the UI thread, name, maker, "Included with the app",
the fit sentence and "N controls missing", which expands to the plain list);
"Can't find yours?" with the Starter Template (copied into My templates, named
after the controller, chosen and returned), the community link and a file from
this computer (the old file dialog, kept as the escape hatch); "Remove
template"; [Cancel] [Use this template].

"Show best matches first" is present but off by default (owner decision: no
proposals switched on). Nothing is pre-selected from a remembered name.

With ``assign=True`` (the default) and a ``device_guid`` the dialog writes the
choice itself (``DeviceService.set_template`` / ``clear_template``); the caller
refreshes. ``pick_template(parent, title, ...)`` is the compatibility entry
point for older call sites: it never assigns and returns the chosen path.
``choose_template(parent, device_guid, ...)`` opens the dialog in assign mode
and returns the ``PickerResult`` (``None`` on Cancel).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import template_catalog
from joystick_diagrams.template_catalog import FitResult, TemplateInfo
from joystick_diagrams.ui import strings_controllers as S
from joystick_diagrams.utils import install_root, user_templates_root

_logger = logging.getLogger(__name__)

SVG_FILTER = S.PICKER_FILE_FILTER
ROLE_INFO = Qt.ItemDataRole.UserRole
ROLE_KIND = Qt.ItemDataRole.UserRole + 1  # "maker" | "template" | "heading"
THUMB_WIDTH = 300

DIALOG_QSS = """
QPushButton, QToolButton { text-transform: none; }
QCheckBox { background: transparent; }
QDialog#templatePicker { background: #1f2229; }
QLabel { background: transparent; }
QLabel#pickerTitle { color: #E8EAED; font-size: 15px; font-weight: 700; }
QLabel#pickerHelp, QLabel#pickerMuted { color: #9AA0A6; font-size: 12px; }
QLabel#pickerHeading { color: #9AA0A6; font-size: 11px; font-weight: 700; }
QLabel#previewName { color: #E8EAED; font-size: 14px; font-weight: 700; }
QLabel#previewFit { color: #E8EAED; font-size: 12px; }
QLabel#previewFit[state="ok"] { color: #34D399; }
QLabel#previewFit[state="warning"] { color: #F59E0B; }
QLabel#missingList { color: #BDC1C6; font-size: 12px; }
QFrame#previewPane, QFrame#cantFind {
    background: #252830; border: 1px solid #3C4043; border-radius: 8px;
}
QPushButton#pickerLink {
    background: transparent; border: none; color: #8AB4F8; padding: 2px 0px;
    text-align: left; font-size: 12px;
}
QPushButton#pickerLink:hover { text-decoration: underline; }
QPushButton#pickerPrimary {
    background: #2F6FDB; color: #ffffff; border: 1px solid #2F6FDB; border-radius: 6px;
    min-height: 36px; padding: 0px 20px; font-weight: 700;
}
QPushButton#pickerPrimary:hover { background: #4C8BF5; border-color: #4C8BF5; }
QPushButton#pickerPrimary:focus { border: 2px solid #4C8BF5; }
QPushButton#pickerPrimary:disabled { background: #3C4043; border-color: #3C4043; color: #6B7280; }
QPushButton#pickerSecondary {
    background: #2c2f38; color: #E8EAED; border: 1px solid #7A808A; border-radius: 6px;
    min-height: 36px; padding: 0px 16px; font-weight: 700;
}
QPushButton#pickerSecondary:hover { border-color: #4C8BF5; }
QTreeWidget#pickerTree { background: #252830; border: 1px solid #3C4043; border-radius: 6px; }
"""


# ── Template files (kept for older callers) ──


def bundled_templates_dir() -> Path:
    return Path(os.path.join(install_root(), "templates"))


def user_templates_has_files() -> bool:
    try:
        return any(user_templates_root().glob("*.svg"))
    except OSError:
        return False


def default_template_dir() -> Path:
    """My templates when it has files, else the bundled folder."""
    if user_templates_has_files():
        return user_templates_root()
    return bundled_templates_dir()


def template_sidebar_urls() -> list[QUrl]:
    urls = [QUrl.fromLocalFile(str(bundled_templates_dir()))]
    try:
        urls.append(QUrl.fromLocalFile(str(user_templates_root())))
    except OSError:
        pass
    return urls


def browse_template_file(
    parent: QWidget | None, title: str | None = None
) -> Path | None:
    """The file dialog: "Use a template file from this computer…"."""
    dialog = QFileDialog(
        parent,
        title or S.PICKER_FILE_DIALOG_TITLE,
        str(default_template_dir()),
        SVG_FILTER,
    )
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setSidebarUrls(template_sidebar_urls())
    if dialog.exec() != QFileDialog.DialogCode.Accepted:
        return None
    files = dialog.selectedFiles()
    return Path(files[0]) if files else None


# ── The controller's bound devices ──


def bound_devices_for(
    guid: str | None, export_devices: Iterable[Any] | None = None
) -> list[Any]:
    """Every ``Device_`` with bindings for ``guid`` (one per profile)."""
    if not guid:
        return []
    devices: list[Any] = []
    if export_devices is not None:
        for export_device in export_devices:
            if getattr(export_device, "device_id", None) == guid:
                device = getattr(export_device, "device", None)
                if device is not None:
                    devices.append(device)
        if devices:
            return devices
    try:
        from joystick_diagrams.app_state import AppState
        from joystick_diagrams.device_status import collect_device_facts

        facts = collect_device_facts(AppState().profile_wrappers).get(guid)
    except Exception as error:  # noqa: BLE001 - a picker without fit still works
        _logger.debug(f"Could not collect bindings for {guid}: {error}")
        return []
    return [device for _wrapper, device in facts.devices] if facts else []


def device_name_for(guid: str | None) -> str | None:
    if not guid:
        return None
    try:
        from joystick_diagrams.app_state import AppState
        from joystick_diagrams.device_status import collect_device_facts

        state = AppState()
        facts = collect_device_facts(state.profile_wrappers).get(guid)
        row = state.device_service.row(guid)
        name = (facts.name if facts else None) or (row.name if row else None)
        return state.device_service.resolve_name(guid, name) if name else None
    except Exception:  # noqa: BLE001
        return None


def fit_sentence(result: FitResult | None, profile_count: int) -> str:
    """The preview pane's sentence ("Every control you use in your 12 profiles…")."""
    if result is None:
        return S.PICKER_FIT_PENDING
    if result.total_bound == 0:
        return S.PICKER_NO_BINDINGS
    if result.fits_all:
        if profile_count:
            return S.PICKER_FITS_ALL.format(
                count=profile_count, profiles=S.plural(profile_count, S.PROFILES)
            )
        return S.PICKER_FITS_ALL_NO_PROFILES
    return S.PICKER_PARTIAL.format(fitted=result.fitted, total=result.total_bound)


# ── Background work ──


class _WorkerSignals(QObject):
    fit_ready = Signal(str, object)  # template key, FitResult | None
    thumb_ready = Signal(str, str)  # template key, png path ("" when unavailable)


class FitRunnable(QRunnable):
    """Computes ``template_catalog.fit`` for each template, one result at a time."""

    def __init__(
        self, infos: list[TemplateInfo], devices: list[Any], signals: _WorkerSignals
    ):
        super().__init__()
        self.infos = infos
        self.devices = devices
        self.signals = signals
        self.cancelled = False

    def run(self) -> None:
        for info in self.infos:
            if self.cancelled:
                return
            try:
                result = template_catalog.fit(info, self.devices)
            except Exception as error:  # noqa: BLE001 - one bad file must not stop the rest
                _logger.debug(f"Fit failed for {info.key}: {error}")
                result = None
            try:
                self.signals.fit_ready.emit(info.key, result)
            except RuntimeError:  # the dialog is gone
                return


class ThumbnailRunnable(QRunnable):
    def __init__(
        self, info: TemplateInfo, signals: _WorkerSignals, width: int = THUMB_WIDTH
    ):
        super().__init__()
        self.info = info
        self.signals = signals
        self.width = width

    def run(self) -> None:
        try:
            path = str(template_catalog.thumbnail_for(self.info, (self.width, None)))
        except Exception as error:  # noqa: BLE001 - a missing preview is not an error
            _logger.debug(f"No thumbnail for {self.info.key}: {error}")
            path = ""
        try:
            self.signals.thumb_ready.emit(self.info.key, path)
        except RuntimeError:
            pass


# ── Dialog ──


@dataclass
class PickerResult:
    path: Path | None = None
    info: TemplateInfo | None = None
    removed: bool = False
    created_from_starter: bool = False


class TemplatePickerDialog(QDialog):
    """Choose a template for one controller (see module doc)."""

    def __init__(
        self,
        device_guid: str | None = None,
        export_devices: Iterable[Any] | None = None,
        parent: QWidget | None = None,
        *,
        device_name: str | None = None,
        assign: bool = True,
        title: str | None = None,
        current_path: str | Path | None = None,
        profile_count: int | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("templatePicker")
        self.setStyleSheet(DIALOG_QSS)
        self.device_guid = device_guid
        self.assign = assign and bool(device_guid)
        self.device_name = device_name or device_name_for(device_guid)
        self.devices = bound_devices_for(device_guid, export_devices)
        self.profile_count = (
            profile_count if profile_count is not None else len(self.devices)
        )
        self.result_value: PickerResult | None = None
        self._fits: dict[str, FitResult | None] = {}
        self._infos: list[TemplateInfo] = []
        self._items: dict[str, QTreeWidgetItem] = {}
        self._selected: TemplateInfo | None = None
        self._pool = QThreadPool.globalInstance()
        self._signals = _WorkerSignals(self)
        self._signals.fit_ready.connect(self._on_fit_ready)
        self._signals.thumb_ready.connect(self._on_thumb_ready)
        self._fit_job: FitRunnable | None = None
        self._current_path = str(current_path) if current_path else self._stored_path()

        heading = (
            S.PICKER_TITLE.format(name=self.device_name)
            if self.device_name
            else S.PICKER_TITLE_NO_DEVICE
        )
        self.setWindowTitle(title or heading)
        self.resize(980, 640)
        self.setMinimumSize(760, 520)
        self._build_ui(heading)
        self.reload()

    @property
    def chosen_path(self) -> Path | None:
        """The chosen template file (``None`` on Cancel or Remove template)."""
        return self.result_value.path if self.result_value is not None else None

    # ── Construction ──

    def _build_ui(self, heading: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        title = QLabel(heading)
        title.setObjectName("pickerTitle")
        title.setWordWrap(True)
        root.addWidget(title)

        search_row = QHBoxLayout()
        search_row.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText(S.PICKER_SEARCH)
        self.search.setToolTip(S.PICKER_SEARCH_TIP)
        self.search.setAccessibleName(S.PICKER_SEARCH_TIP)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._rebuild_tree)
        search_row.addWidget(self.search, 1)
        self.sort_by_fit = QCheckBox(S.PICKER_SORT_BY_FIT)
        self.sort_by_fit.setChecked(False)
        self.sort_by_fit.toggled.connect(self._rebuild_tree)
        search_row.addWidget(self.sort_by_fit)
        root.addLayout(search_row)

        help_label = QLabel(S.PICKER_COUNTS_HELP)
        help_label.setObjectName("pickerHelp")
        root.addWidget(help_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        self.tree = QTreeWidget()
        self.tree.setObjectName("pickerTree")
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.currentItemChanged.connect(self._on_current_changed)
        self.tree.itemDoubleClicked.connect(self._on_double_clicked)
        left_layout.addWidget(self.tree, 1)
        self.no_results = QLabel("")
        self.no_results.setObjectName("pickerMuted")
        self.no_results.hide()
        left_layout.addWidget(self.no_results)
        left_layout.addWidget(self._build_cant_find())
        splitter.addWidget(left)

        splitter.addWidget(self._build_preview())
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)
        root.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.remove_button = QPushButton(S.PICKER_REMOVE)
        self.remove_button.setObjectName("pickerSecondary")
        self.remove_button.clicked.connect(self._remove_template)
        self.remove_button.setVisible(self.assign and bool(self._current_path))
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        self.cancel_button = QPushButton(S.PICKER_CANCEL)
        self.cancel_button.setObjectName("pickerSecondary")
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        self.use_button = QPushButton(S.PICKER_USE)
        self.use_button.setObjectName("pickerPrimary")
        self.use_button.setDefault(True)
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self._use_selected)
        buttons.addWidget(self.use_button)
        root.addLayout(buttons)
        self.search.setFocus()

    def _build_cant_find(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("cantFind")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        heading = QLabel(S.PICKER_CANT_FIND)
        heading.setObjectName("pickerHeading")
        layout.addWidget(heading)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.starter_button = QPushButton(S.PICKER_USE_STARTER)
        self.starter_button.setObjectName("pickerSecondary")
        self.starter_button.clicked.connect(self._use_starter)
        row.addWidget(self.starter_button)
        starter_help = QLabel(
            S.PICKER_STARTER_HELP.format(name=self.device_name)
            if self.device_name
            else S.PICKER_STARTER_HELP_NO_DEVICE
        )
        starter_help.setObjectName("pickerMuted")
        starter_help.setWordWrap(True)
        row.addWidget(starter_help, 1)
        layout.addLayout(row)
        links = QHBoxLayout()
        links.setSpacing(4)
        self.community_link = QPushButton(S.PICKER_COMMUNITY)
        self.community_link.setObjectName("pickerLink")
        self.community_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.community_link.clicked.connect(self._open_community)
        links.addWidget(self.community_link)
        dot = QLabel("·")
        dot.setObjectName("pickerMuted")
        links.addWidget(dot)
        self.file_link = QPushButton(S.PICKER_FROM_FILE)
        self.file_link.setObjectName("pickerLink")
        self.file_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_link.clicked.connect(self._use_file)
        links.addWidget(self.file_link)
        links.addStretch(1)
        layout.addLayout(links)
        self.problem_label = QLabel("")
        self.problem_label.setObjectName("pickerMuted")
        self.problem_label.setStyleSheet("color: #F87171;")
        self.problem_label.setWordWrap(True)
        self.problem_label.hide()
        layout.addWidget(self.problem_label)
        return frame

    def _build_preview(self) -> QFrame:
        pane = QFrame()
        pane.setObjectName("previewPane")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setMinimumHeight(220)
        layout.addWidget(self.thumbnail, 1)
        self.preview_name = QLabel(S.PICKER_PREVIEW_EMPTY)
        self.preview_name.setObjectName("previewName")
        self.preview_name.setWordWrap(True)
        layout.addWidget(self.preview_name)
        self.preview_source = QLabel("")
        self.preview_source.setObjectName("pickerMuted")
        layout.addWidget(self.preview_source)
        self.preview_fit = QLabel("")
        self.preview_fit.setObjectName("previewFit")
        self.preview_fit.setWordWrap(True)
        layout.addWidget(self.preview_fit)
        self.missing_toggle = QPushButton("")
        self.missing_toggle.setObjectName("pickerLink")
        self.missing_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.missing_toggle.setToolTip(S.MISSING_CONTROLS_TIP)
        self.missing_toggle.clicked.connect(self._toggle_missing)
        self.missing_toggle.hide()
        layout.addWidget(self.missing_toggle)
        self.missing_list = QLabel("")
        self.missing_list.setObjectName("missingList")
        self.missing_list.setWordWrap(True)
        self.missing_list.hide()
        layout.addWidget(self.missing_list)
        return pane

    # ── Data ──

    def _stored_path(self) -> str | None:
        if not self.device_guid:
            return None
        try:
            from joystick_diagrams.app_state import AppState

            ref = AppState().device_service.template(self.device_guid)
        except Exception:  # noqa: BLE001
            return None
        return ref.path if ref else None

    def reload(self) -> None:
        """Enumerate the catalogue again and start the fit counts."""
        try:
            self._infos = [
                info for info in template_catalog.all_templates() if not info.is_starter
            ]
        except Exception as error:  # noqa: BLE001
            _logger.error(f"Could not list templates: {error}", exc_info=True)
            self._infos = []
        self._rebuild_tree()
        self._start_fits()
        self._select_current()

    def _start_fits(self) -> None:
        if self._fit_job is not None:
            self._fit_job.cancelled = True
        pending = [info for info in self._infos if info.key not in self._fits]
        if not pending:
            return
        self._fit_job = FitRunnable(pending, self.devices, self._signals)
        self._pool.start(self._fit_job)

    def wait_for_fits(self, timeout_ms: int = 30000) -> bool:
        """Tests: block until every fit count is in (processes queued signals)."""
        from PySide6.QtCore import QCoreApplication, QElapsedTimer

        timer = QElapsedTimer()
        timer.start()
        while timer.elapsed() < timeout_ms:
            QCoreApplication.processEvents()
            if all(info.key in self._fits for info in self._infos):
                return True
            self._pool.waitForDone(20)
        return False

    def fit_for(self, info: TemplateInfo) -> FitResult | None:
        return self._fits.get(info.key)

    # ── Tree ──

    def _matches(self, info: TemplateInfo, query: str) -> bool:
        if not query:
            return True
        return query in info.name.casefold() or query in (info.maker or "").casefold()

    def _row_fit_text(self, info: TemplateInfo) -> str:
        if info.key not in self._fits:
            return S.PICKER_FIT_PENDING
        result = self._fits[info.key]
        return template_catalog.fit_text(result) if result is not None else ""

    def _rebuild_tree(self, *_args) -> None:
        query = self.search.text().strip().casefold()
        selected_key = self._selected.key if self._selected else None
        self.tree.blockSignals(True)
        self.tree.clear()
        self._items = {}
        shown = [info for info in self._infos if self._matches(info, query)]
        bundled = [info for info in shown if info.source == "bundled"]
        mine = [info for info in shown if info.source != "bundled"]

        if self.sort_by_fit.isChecked():
            for info in sorted(shown, key=self._fit_sort_key):
                self.tree.addTopLevelItem(self._template_item(info))
        else:
            heading = QTreeWidgetItem([S.PICKER_ALL_BY_MAKER, ""])
            heading.setData(0, ROLE_KIND, "heading")
            heading.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tree.addTopLevelItem(heading)
            for maker in template_catalog.makers(bundled):
                members = [info for info in bundled if info.maker == maker]
                self.tree.addTopLevelItem(self._group_item(maker, members, bool(query)))
            self.tree.addTopLevelItem(
                self._group_item(S.PICKER_MY_TEMPLATES, mine, bool(query) or bool(mine))
            )
        self.tree.resizeColumnToContents(1)
        self.tree.setColumnWidth(
            0, max(260, self.tree.width() - self.tree.columnWidth(1) - 30)
        )
        self.no_results.setVisible(bool(query) and not shown)
        self.no_results.setText(
            S.PICKER_NO_RESULTS.format(query=self.search.text().strip())
        )
        self.tree.blockSignals(False)
        if selected_key and selected_key in self._items:
            self.tree.setCurrentItem(self._items[selected_key])

    def _fit_sort_key(self, info: TemplateInfo) -> tuple[int, int, str]:
        result = self._fits.get(info.key)
        if result is None:
            return (2, 0, info.name.casefold())
        return (0 if result.fits_all else 1, -result.fitted, info.name.casefold())

    def _group_item(
        self, label: str, members: list[TemplateInfo], expand: bool
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label, str(len(members))])
        item.setData(0, ROLE_KIND, "maker")
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setTextAlignment(
            1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        for info in members:
            item.addChild(self._template_item(info))
        item.setExpanded(expand)
        return item

    def _template_item(self, info: TemplateInfo) -> QTreeWidgetItem:
        item = QTreeWidgetItem([info.name, self._row_fit_text(info)])
        item.setData(0, ROLE_INFO, info)
        item.setData(0, ROLE_KIND, "template")
        item.setToolTip(0, info.name)
        self._paint_fit(item, info)
        self._items[info.key] = item
        return item

    def _paint_fit(self, item: QTreeWidgetItem, info: TemplateInfo) -> None:
        from PySide6.QtGui import QBrush, QColor

        result = self._fits.get(info.key)
        colour = "#9AA0A6"
        if result is not None and result.total_bound:
            colour = "#34D399" if result.fits_all else "#F59E0B"
        item.setForeground(1, QBrush(QColor(colour)))

    def _select_current(self) -> None:
        if not self._current_path:
            return
        try:
            info = template_catalog.info_for_path(Path(self._current_path))
        except Exception:  # noqa: BLE001 - a vanished file has no row
            return
        item = self._items.get(info.key)
        if item is not None:
            parent = item.parent()
            if parent is not None:
                parent.setExpanded(True)
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)

    def template_items(self) -> list[QTreeWidgetItem]:
        return list(self._items.values())

    def select_template(self, key: str) -> bool:
        item = self._items.get(key)
        if item is None:
            return False
        parent = item.parent()
        if parent is not None:
            parent.setExpanded(True)
        self.tree.setCurrentItem(item)
        return True

    # ── Signals from workers ──

    def _on_fit_ready(self, key: str, result: FitResult | None) -> None:
        self._fits[key] = result
        item = self._items.get(key)
        if item is not None:
            info = item.data(0, ROLE_INFO)
            item.setText(1, self._row_fit_text(info))
            self._paint_fit(item, info)
        if self._selected is not None and self._selected.key == key:
            self._show_fit(self._selected)
        if self.sort_by_fit.isChecked() and all(
            i.key in self._fits for i in self._infos
        ):
            self._rebuild_tree()

    def _on_thumb_ready(self, key: str, path: str) -> None:
        if self._selected is None or self._selected.key != key:
            return
        if not path:
            self.thumbnail.setPixmap(
                qta.icon("fa5s.gamepad", color="#5F6368").pixmap(QSize(96, 96))
            )
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        target = self.thumbnail.size()
        self.thumbnail.setPixmap(
            pixmap.scaled(
                max(target.width(), 120),
                max(target.height(), 120),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ── Selection and preview ──

    def _on_current_changed(
        self, current: QTreeWidgetItem | None, _previous=None
    ) -> None:
        info = current.data(0, ROLE_INFO) if current is not None else None
        if not isinstance(info, TemplateInfo):
            self._selected = None
            self.use_button.setEnabled(False)
            return
        self._selected = info
        self.use_button.setEnabled(True)
        self.preview_name.setText(info.name)
        from joystick_diagrams.ui.controllers_page import source_parts

        parts = source_parts(info)
        self.preview_source.setText(" · ".join(parts))
        self._show_fit(info)
        self.thumbnail.setPixmap(
            qta.icon("fa5s.sync", color="#5F6368").pixmap(QSize(28, 28))
        )
        self._pool.start(ThumbnailRunnable(info, self._signals))

    def _show_fit(self, info: TemplateInfo) -> None:
        result = self._fits.get(info.key) if info.key in self._fits else None
        pending = info.key not in self._fits
        self.preview_fit.setText(
            S.PICKER_FIT_PENDING
            if pending
            else fit_sentence(result, self.profile_count)
        )
        state = ""
        if result is not None and result.total_bound:
            state = "ok" if result.fits_all else "warning"
        self.preview_fit.setProperty("state", state)
        self.preview_fit.style().unpolish(self.preview_fit)
        self.preview_fit.style().polish(self.preview_fit)
        missing = list(result.missing) if result is not None else []
        self.missing_list.setText(", ".join(missing))
        self.missing_list.hide()
        if missing:
            self.missing_toggle.setText(
                S.PICKER_SHOW_MISSING.format(
                    count=len(missing), controls=S.plural(len(missing), S.CONTROLS)
                )
            )
            self.missing_toggle.show()
        else:
            self.missing_toggle.hide()

    def _toggle_missing(self) -> None:
        showing = not self.missing_list.isVisible()
        self.missing_list.setVisible(showing)
        if showing:
            self.missing_toggle.setText(S.PICKER_HIDE_MISSING)
        elif self._selected is not None:
            self._show_fit(self._selected)

    def _on_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if isinstance(item.data(0, ROLE_INFO), TemplateInfo):
            self._use_selected()

    # ── Actions ──

    def _finish(self, result: PickerResult) -> None:
        if self.assign and self.device_guid:
            from joystick_diagrams.app_state import AppState

            service = AppState().device_service
            if result.removed:
                service.clear_template(self.device_guid)
            elif result.path is not None:
                service.set_template(self.device_guid, result.path)
        self.result_value = result
        if self._fit_job is not None:
            self._fit_job.cancelled = True
        self.accept()

    def _use_selected(self) -> None:
        if self._selected is None:
            return
        self._finish(PickerResult(path=self._selected.path, info=self._selected))

    def _use_starter(self) -> None:
        try:
            created = template_catalog.create_from_starter(
                self.device_name or template_catalog.FALLBACK_DEVICE_NAME
            )
        except Exception as error:  # noqa: BLE001 - say so in place, keep the dialog
            _logger.error(f"Starter Template copy failed: {error}", exc_info=True)
            self.problem_label.setText(S.PICKER_STARTER_FAILED.format(detail=error))
            self.problem_label.show()
            return
        self._finish(
            PickerResult(
                path=created.path, info=created.info, created_from_starter=True
            )
        )

    def _use_file(self) -> None:
        path = browse_template_file(self)
        if path is None:
            return
        info = None
        try:
            info = template_catalog.info_for_path(path)
        except Exception:  # noqa: BLE001 - a file outside the catalogue is fine
            info = None
        self._finish(PickerResult(path=path, info=info))

    def _remove_template(self) -> None:
        self._finish(PickerResult(removed=True))

    def _open_community(self) -> None:
        QDesktopServices.openUrl(QUrl(S.PICKER_COMMUNITY_URL))

    def reject(self) -> None:  # noqa: D401 - Qt override
        if self._fit_job is not None:
            self._fit_job.cancelled = True
        super().reject()


# ── Entry points ──


def choose_template(
    parent: QWidget | None,
    device_guid: str,
    export_devices: Iterable[Any] | None = None,
    device_name: str | None = None,
    profile_count: int | None = None,
) -> PickerResult | None:
    """Open the picker for ``device_guid`` and store the choice; ``None`` on Cancel."""
    dialog = TemplatePickerDialog(
        device_guid,
        export_devices,
        parent,
        device_name=device_name,
        assign=True,
        profile_count=profile_count,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.result_value


def pick_template(
    parent: QWidget | None,
    title: str | None = None,
    device_guid: str | None = None,
    export_devices: Iterable[Any] | None = None,
    device_name: str | None = None,
) -> Path | None:
    """Compatibility: open the picker and return the chosen path (never assigns)."""
    dialog = TemplatePickerDialog(
        device_guid,
        export_devices,
        parent,
        device_name=device_name,
        assign=False,
        title=title,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result_value is None:
        return None
    return dialog.result_value.path


if __name__ == "__main__":
    pass
