"""Empty state shown on the Plugin Setup page when no plugins are installed.

Catalog-agnostic and AppState-free: the page supplies catalog entries (or reports the
catalog unavailable) and this widget emits intent signals. It never installs anything
itself, which keeps it testable without a network, a database, or the app singleton.
"""

from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.ui.widgets.drop_zone import DropZoneWidget

_PICKER_COLUMNS = 2
_UNAVAILABLE_TEXT = (
    "Couldn't reach the plugin catalog. You can still install a plugin manually below."
)


class PluginEmptyState(QWidget):
    """Zero-plugin state: hero, a state-dependent picker, and an always-present action row."""

    install_requested = Signal(list)  # list[CatalogEntry] — the checked entries
    browse_store_requested = Signal()
    install_zip_requested = (
        Signal()
    )  # button has no path; the page raises a file dialog
    zip_dropped = Signal(Path)  # drop zone already carries a path
    retry_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._checkboxes: list[tuple[QCheckBox, object]] = []
        self._install_button: QPushButton | None = None
        self._build_ui()
        self.set_loading()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(14)
        root.addStretch(1)

        icon = QLabel()
        icon.setPixmap(
            qta.icon("fa5s.puzzle-piece", color="#4C8BF5").pixmap(QSize(48, 48))
        )
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(icon)

        heading = QLabel("No plugins installed yet")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet("color: #E8EAED; font-size: 16px; font-weight: bold;")
        root.addWidget(heading)

        blurb = QLabel(
            "Plugins read your game's keybind files and turn them into diagrams."
        )
        blurb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        blurb.setWordWrap(True)
        blurb.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        root.addWidget(blurb)

        # Picker — the only zone that changes with catalog state.
        self._picker = QFrame()
        self._picker.setProperty("class", "surface-card")
        self._picker.setMaximumWidth(520)
        self._picker_layout = QVBoxLayout(self._picker)
        self._picker_layout.setContentsMargins(16, 14, 16, 14)
        self._picker_layout.setSpacing(10)
        root.addWidget(self._picker, alignment=Qt.AlignmentFlag.AlignCenter)

        # Action row — identical in every state, including offline.
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.browse_button = QPushButton("Browse plugin store")
        self.browse_button.setProperty("class", "plugin-setup-button")
        self.browse_button.setIcon(qta.icon("fa5s.puzzle-piece", color="#E8EAED"))
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self.browse_store_requested.emit)
        actions.addWidget(self.browse_button)

        self.zip_button = QPushButton("Install from ZIP...")
        self.zip_button.setProperty("class", "plugin-setup-button")
        self.zip_button.setIcon(qta.icon("fa5s.file-archive", color="#E8EAED"))
        self.zip_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zip_button.clicked.connect(self.install_zip_requested.emit)
        actions.addWidget(self.zip_button)

        root.addLayout(actions)

        self.drop_zone = DropZoneWidget(
            "or drag & drop a plugin ZIP here", compact=True
        )
        self.drop_zone.file_dropped.connect(self.zip_dropped.emit)
        root.addWidget(self.drop_zone, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addStretch(2)

    # ------------------------------------------------------------------
    # States
    # ------------------------------------------------------------------

    def set_loading(self) -> None:
        self._clear_picker()
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spinner = QLabel()
        spinner.setPixmap(
            qta.icon("fa5s.spinner", color="#9AA0A6").pixmap(QSize(16, 16))
        )
        spinner.setFixedSize(16, 16)
        row.addWidget(spinner)
        row.addWidget(self._muted_label("Finding available plugins..."))
        self._picker_layout.addLayout(row)

    def set_catalog(self, entries: list) -> None:
        if not entries:
            # An empty catalog behaves like an unreachable one, so the user still
            # gets a Retry alongside the manual route.
            self.set_unavailable("No plugins are listed in the catalog.")
            return

        self._clear_picker()

        prompt = QLabel("Which games do you play?")
        prompt.setStyleSheet("color: #E8EAED; font-weight: bold;")
        self._picker_layout.addWidget(prompt)

        self._install_button = QPushButton()
        self._install_button.setProperty("class", "run-button")
        self._install_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._install_button.clicked.connect(self._emit_install)

        grid = QGridLayout()
        grid.setSpacing(8)
        for index, entry in enumerate(entries):
            box = QCheckBox(entry.name)
            box.setToolTip(getattr(entry, "description", "") or entry.name)
            box.stateChanged.connect(self._sync_install_button)
            grid.addWidget(box, index // _PICKER_COLUMNS, index % _PICKER_COLUMNS)
            self._checkboxes.append((box, entry))
        self._picker_layout.addLayout(grid)

        self._picker_layout.addWidget(self._install_button)
        self._sync_install_button()

    def set_unavailable(self, reason: str | None = None) -> None:
        self._clear_picker()
        self._picker_layout.addWidget(self._muted_label(reason or _UNAVAILABLE_TEXT))

        retry = QPushButton("Retry")
        retry.setProperty("class", "plugin-setup-button")
        retry.setCursor(Qt.CursorShape.PointingHandCursor)
        retry.clicked.connect(self.retry_requested.emit)
        self._picker_layout.addWidget(retry, alignment=Qt.AlignmentFlag.AlignCenter)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def selected_entries(self) -> list:
        return [entry for box, entry in self._checkboxes if box.isChecked()]

    def _sync_install_button(self) -> None:
        if self._install_button is None:
            return
        count = len(self.selected_entries())
        self._install_button.setEnabled(count > 0)
        if count:
            plural = "s" if count != 1 else ""
            self._install_button.setText(f"Install {count} plugin{plural}")
        else:
            self._install_button.setText("Select a plugin to install")

    def _emit_install(self) -> None:
        entries = self.selected_entries()
        if entries:
            self.install_requested.emit(entries)

    def _clear_picker(self) -> None:
        self._checkboxes.clear()
        self._install_button = None
        self._clear_layout(self._picker_layout)

    @staticmethod
    def _clear_layout(layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                PluginEmptyState._clear_layout(item.layout())

    @staticmethod
    def _muted_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        return label
