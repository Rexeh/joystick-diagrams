import logging

import qtawesome as qta
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui.customise_devices import CustomiseDevices
from joystick_diagrams.ui.customise_inheritance import CustomiseInheritance
from joystick_diagrams.ui.customise_labels import CustomiseLabels
from joystick_diagrams.ui.customise_profiles import CustomiseProfiles
from joystick_diagrams.ui.qt_designer import configure_page_ui
from joystick_diagrams.ui.widgets.section_header import SectionHeader

_logger = logging.getLogger(__name__)


class configurePage(QMainWindow, configure_page_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Replace heading with SectionHeader
        self.heading_label.hide()
        self.section_header = SectionHeader(
            "fa5s.tools",
            "Customise & Review",
            "View binds, edit labels, manage devices, and configure profile inheritance",
        )
        self.verticalLayout.insertWidget(0, self.section_header)

        # Hide the tab widget — we replace it with sidebar navigation
        self.tabWidget.hide()

        # Left sidebar navigation (same pattern as settings_page.py)
        container = QWidget()
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setProperty("class", "settings-nav")

        nav_items = [
            ("fa5s.sliders-h", "Profiles"),
            ("fa5s.code-branch", "Inheritance"),
            ("fa5s.hdd", "Devices"),
            ("fa5s.tags", "Labels"),
        ]
        for icon_name, label in nav_items:
            item = QListWidgetItem(qta.icon(icon_name, color="#9AA0A6"), label)
            item.setSizeHint(QSize(0, 44))
            self.nav_list.addItem(item)

        root_layout.addWidget(self.nav_list)

        # Content stack
        self.stack = QStackedWidget()

        self.profiles_screen = CustomiseProfiles()
        self.inheritance_screen = CustomiseInheritance()
        self.devices_screen = CustomiseDevices()
        self.labels_screen = CustomiseLabels()

        self.stack.addWidget(self.profiles_screen)
        self.stack.addWidget(self.inheritance_screen)
        self.stack.addWidget(self.devices_screen)
        self.stack.addWidget(self.labels_screen)

        root_layout.addWidget(self.stack, 1)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)

        self.verticalLayout.addWidget(container)

        # Wire cross-screen signals
        self.devices_screen.devices_changed.connect(self._on_devices_changed)
        self.profiles_screen.device_visibility_changed.connect(
            self.devices_screen.refresh
        )

        # Initial load
        self.profiles_screen.refresh()

    def _on_nav_changed(self, row: int):
        self.stack.setCurrentIndex(row)
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()

    def _on_devices_changed(self):
        self.profiles_screen.refresh()
        # Refresh the Export page device tree if it has been loaded
        main_window = self.appState.main_window
        if main_window and main_window._export_page is not None:
            main_window._export_page.device_widget.devices_updated.emit()

    def refresh(self):
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()


if __name__ == "__main__":
    pass
