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
from joystick_diagrams.ui import strings_appearance, strings_layout
from joystick_diagrams.ui.customise_appearance import CustomiseAppearance
from joystick_diagrams.ui.customise_devices import CustomiseDevices
from joystick_diagrams.ui.customise_inheritance import CustomiseInheritance
from joystick_diagrams.ui.customise_labels import CustomiseLabels
from joystick_diagrams.ui.customise_layout import CustomiseLayout
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
            strings_appearance.CUSTOMISE_SUBTITLE,
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
            ("fa5s.palette", strings_appearance.NAV_APPEARANCE),
            ("fa5s.th-large", strings_layout.NAV_LAYOUT),
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
        self.appearance_screen = CustomiseAppearance()
        self.layout_screen = CustomiseLayout()

        self.stack.addWidget(self.profiles_screen)
        self.stack.addWidget(self.inheritance_screen)
        self.stack.addWidget(self.devices_screen)
        self.stack.addWidget(self.labels_screen)
        self.stack.addWidget(self.appearance_screen)
        self.stack.addWidget(self.layout_screen)

        root_layout.addWidget(self.stack, 1)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)

        self.verticalLayout.addWidget(container)

        # Wire cross-screen signals
        self.devices_screen.devices_changed.connect(self._on_devices_changed)
        self.profiles_screen.device_visibility_changed.connect(
            self.devices_screen.refresh
        )
        self.devices_screen.edit_layout_requested.connect(self.show_layout)
        self.layout_screen.devices_changed.connect(self._on_devices_changed)
        self.layout_screen.devices_changed.connect(self.devices_screen.refresh)

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

    def show_appearance(self, tab: int = CustomiseAppearance.TAB_STYLE):
        """Navigate to Customise → Appearance and open the given tab."""
        self.appearance_screen.show_tab(tab)
        self.nav_list.setCurrentRow(self.stack.indexOf(self.appearance_screen))

    def show_layout(self, device_id: str | None = None):
        """Navigate to Customise → Layout with ``device_id``'s diagram selected."""
        self.nav_list.setCurrentRow(self.stack.indexOf(self.layout_screen))
        self.layout_screen.show_device(device_id)

    def shutdown(self):
        """Tear down WebEngine pages before the page is destroyed (plan §5.6)."""
        self.layout_screen.shutdown()
        preview = getattr(self.appearance_screen.style_tab, "preview", None)
        if preview is not None:
            preview.shutdown()


if __name__ == "__main__":
    pass
