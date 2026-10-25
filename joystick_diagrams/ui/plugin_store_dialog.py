"""The game list dialog ("Games and other apps"): browse the hosted catalogue and
add or update games and other apps (plugins, in code).

Fetches ``plugins_manifest.json`` off the UI thread, classifies each entry against
what is added, and adds or updates through the shared install + trust flow.
Signed entries show a Verified chip; the rest show Community and go through the
community check. A finished add is one inline line, never a dialog.
"""

import logging

import qtawesome as qta
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.plugins import plugin_catalog as pc
from joystick_diagrams.ui import strings_setup as S
from joystick_diagrams.ui.plugin_install_flow import install_from_catalog

_logger = logging.getLogger(__name__)


class _FetchSignals(QObject):
    finished = Signal(object)  # PluginCatalog | None


class _FetchWorker(QRunnable):
    """Fetches the plugin catalog off the UI thread."""

    def __init__(self):
        super().__init__()
        self.signals = _FetchSignals()

    @Slot()
    def run(self):
        catalog = pc.fetch_catalog()
        self.signals.finished.emit(catalog)


class PluginStoreDialog(QDialog):
    catalog_changed = Signal()  # emitted after a successful install/update

    def __init__(self, parent=None):
        super().__init__(parent)
        self.appState = AppState()
        self._catalog: pc.PluginCatalog | None = None
        self._thread_pool = QThreadPool()
        self._worker: _FetchWorker | None = None

        self.setWindowTitle(S.STORE_TITLE)
        self.setMinimumSize(640, 520)
        self._build_ui()
        self._load()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        title = QLabel(S.STORE_TITLE)
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        outer.addWidget(title)

        subtitle = QLabel(S.STORE_INTRO)
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        outer.addWidget(self._progress)

        self._done_label = QLabel()
        self._done_label.setStyleSheet("color: #34D399;")
        self._done_label.hide()
        outer.addWidget(self._done_label)

        self._status_label = QLabel(S.STORE_LOADING)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._status_label)

        self._rows_scroll = QScrollArea()
        self._rows_scroll.setWidgetResizable(True)
        self._rows_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        self._rows_layout.addStretch()
        self._rows_scroll.setWidget(self._rows_container)
        outer.addWidget(self._rows_scroll, stretch=1)

        button_row = QHBoxLayout()
        self._refresh_btn = QPushButton(S.STORE_CHECK_AGAIN)
        self._refresh_btn.setIcon(qta.icon("fa5s.sync", color="white"))
        self._refresh_btn.clicked.connect(self._load)
        button_row.addWidget(self._refresh_btn)
        button_row.addStretch()
        close_btn = QPushButton(S.STORE_CLOSE)
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)
        outer.addLayout(button_row)

    # ── Loading ──

    def _load(self):
        self._refresh_btn.setEnabled(False)
        self._progress.show()
        self._status_label.setText(S.STORE_LOADING)
        self._status_label.show()
        self._clear_rows()
        self._worker = _FetchWorker()
        self._worker.signals.finished.connect(self._on_fetched)
        self._thread_pool.start(self._worker)

    def _on_fetched(self, catalog: pc.PluginCatalog | None):
        self._progress.hide()
        self._refresh_btn.setEnabled(True)
        if catalog is None:
            self._status_label.setText(S.STORE_OFFLINE)
            return
        self._catalog = catalog
        self._rebuild_rows()

    def _rebuild_rows(self):
        self._clear_rows()
        if self._catalog is None:
            return

        installed = pc.installed_index(
            self.appState.plugin_manager, self.appState.output_plugin_manager
        )
        statuses = pc.compute_status(self._catalog, installed)

        if not statuses:
            self._status_label.setText(S.STORE_EMPTY)
            self._status_label.show()
            return

        self._status_label.hide()
        for item in statuses:
            self._rows_layout.insertWidget(
                self._rows_layout.count() - 1, self._make_row(item)
            )

    def _clear_rows(self):
        while self._rows_layout.count() > 1:  # keep the trailing stretch
            item = self._rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Row widgets ──

    def _make_row(self, item: pc.CatalogItemStatus) -> QWidget:
        entry = item.entry
        row = QFrame()
        row.setProperty("class", "plugin-card")
        row.setMinimumHeight(64)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        center = QVBoxLayout()
        center.setSpacing(3)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_label = QLabel(entry.name)
        name_label.setProperty("class", "plugin-card-name")
        name_row.addWidget(name_label)
        name_row.addWidget(QLabel(S.STORE_VERSION.format(version=entry.version)))
        name_row.addWidget(self._type_badge(entry.type))
        name_row.addWidget(self._trust_badge(entry.signed))
        name_row.addStretch()
        center.addLayout(name_row)

        if entry.description:
            desc = QLabel(entry.description)
            desc.setWordWrap(True)
            desc.setProperty("class", "plugin-card-status")
            center.addWidget(desc)

        layout.addLayout(center, stretch=1)
        layout.addWidget(self._action_button(item))
        return row

    def _action_button(self, item: pc.CatalogItemStatus) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("class", "plugin-setup-button")
        btn.setMinimumWidth(120)

        if not item.compatible:
            btn.setText(S.PICKER_NEEDS_APP.format(version=item.entry.min_app_version))
            btn.setEnabled(False)
        elif item.status is pc.CatalogStatus.INSTALLED:
            btn.setText(S.STORE_ADDED)
            btn.setEnabled(False)
        elif item.status is pc.CatalogStatus.UPDATE_AVAILABLE:
            btn.setText(S.STORE_UPDATE.format(version=item.entry.version))
            btn.setToolTip(S.STORE_UPDATE_TIP.format(version=item.installed_version))
            btn.clicked.connect(lambda: self._on_action(item))
        else:  # AVAILABLE
            btn.setText(S.STORE_ADD)
            btn.clicked.connect(lambda: self._on_action(item))
        return btn

    @staticmethod
    def _type_badge(plugin_type: str) -> QLabel:
        badge = QLabel(
            S.STORE_TYPE_GAME if plugin_type == "parser" else S.STORE_TYPE_APP
        )
        badge.setStyleSheet(
            "color: #9AA0A6; background: rgba(154, 160, 166, 0.15); "
            "border-radius: 3px; padding: 1px 6px; font-size: 10px;"
        )
        badge.setFixedHeight(16)
        return badge

    @staticmethod
    def _trust_badge(signed: bool) -> QLabel:
        if signed:
            badge = QLabel(S.PICKER_VERIFIED)
            badge.setToolTip(S.STORE_VERIFIED_TIP)
            badge.setStyleSheet(
                "color: #34D399; background: rgba(52, 211, 153, 0.15); "
                "border-radius: 3px; padding: 1px 6px; font-size: 10px;"
            )
        else:
            badge = QLabel(S.PICKER_COMMUNITY)
            badge.setToolTip(S.STORE_COMMUNITY_TIP)
            badge.setStyleSheet(
                "color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                "border-radius: 3px; padding: 1px 6px; font-size: 10px;"
            )
        badge.setFixedHeight(16)
        return badge

    # ── Actions ──

    def _on_action(self, item: pc.CatalogItemStatus):
        name = install_from_catalog(item.entry, self.appState, self)
        if name is None:
            return
        self._done_label.setText(S.STORE_DONE.format(name=name))
        self._done_label.show()
        self.catalog_changed.emit()
        self._rebuild_rows()
