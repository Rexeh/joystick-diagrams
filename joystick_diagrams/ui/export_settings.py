import logging
import os
import sys

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
)

from joystick_diagrams.db.db_settings import add_update_setting_value, get_setting
from joystick_diagrams.render.theme import (
    ORIGINAL_THEME_NAME,
    TEMPLATE_ORIGINAL_THEME_ID,
)
from joystick_diagrams.ui import strings_appearance
from joystick_diagrams.ui.qt_designer import export_settings
from joystick_diagrams.utils import install_root

_logger = logging.getLogger(__name__)

EXPORT_PATH_SETTING_KEY = "export_path"
EXPORT_FORMAT_SETTING_KEY = "export_format"


class ExportSettings(QMainWindow, export_settings.Ui_Form):
    export_path_changed = Signal()
    edit_style_requested = Signal()
    style_changed = Signal(str)  # theme id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        # Attributes
        self.export_location = None

        # Connections
        self.setExportLocationButton.clicked.connect(self.set_export_location)
        self.setExportLocationButton.setProperty("class", "export-location-button")
        self.export_path_changed.connect(self.setup_widget)

        # Export format setup
        self.export_format.clear()
        self.export_format.addItem("SVG", "SVG")
        self.export_format.addItem("PNG", "PNG")
        self.export_format.setProperty("class", "view-binds-list")

        saved_format = get_setting(EXPORT_FORMAT_SETTING_KEY) or "SVG"
        index = self.export_format.findData(saved_format)
        if index >= 0:
            self.export_format.setCurrentIndex(index)

        self.export_format.currentIndexChanged.connect(self._on_format_changed)

        # Style row (programmatic: the designer file is generated, plan §5.5.2)
        self._build_style_row()

        # Setup
        self.setup_widget()

        # Styling Overrides

    def setup_widget(self):
        export_location = self.get_export_location()

        if export_location:
            self.export_location_directory.setText(export_location)
            self.setExportLocationButton.setText("Change Export Location")
            self.export_location = export_location
            return

        self.export_location_directory.setText("Not Selected")
        self.setExportLocationButton.setText("Set Export Location")

    def get_export_location(self):
        """Gets the stored export location if available"""
        return get_setting(EXPORT_PATH_SETTING_KEY)

    def store_export_location(self, location: str):
        add_update_setting_value(EXPORT_PATH_SETTING_KEY, location)

    def get_export_format(self) -> str:
        return self.export_format.currentData() or "SVG"

    # ── Style row ──

    def _build_style_row(self):
        """ "Style: [combo] Edit…" next to Export Format, bound to the active style."""
        self.export_format_container.addSpacing(16)
        self.export_style_label = QLabel(strings_appearance.EXPORT_STYLE_LABEL)
        font = self.export_format_label.font()
        self.export_style_label.setFont(font)
        self.export_format_container.addWidget(self.export_style_label)

        self.export_style = QComboBox()
        self.export_style.setProperty("class", "view-binds-list")
        self.export_style.setMinimumWidth(180)
        self.export_style.currentIndexChanged.connect(self._on_style_changed)
        self.export_format_container.addWidget(self.export_style)

        self.edit_style_button = QPushButton(strings_appearance.EXPORT_STYLE_EDIT)
        self.edit_style_button.setProperty("class", "plugin-setup-button")
        self.edit_style_button.clicked.connect(self.edit_style_requested.emit)
        self.export_format_container.addWidget(self.edit_style_button)
        self.export_format_container.addStretch(1)
        self.refresh_style_combo()

    @staticmethod
    def _theme_service():
        from joystick_diagrams.app_state import AppState

        return AppState().theme_service if AppState._inst is not None else None

    def refresh_style_combo(self):
        """Rebuild the style list from the theme service and select the active style."""
        service = self._theme_service()
        self.export_style.blockSignals(True)
        self.export_style.clear()
        self.export_style.addItem(ORIGINAL_THEME_NAME, TEMPLATE_ORIGINAL_THEME_ID)
        active = TEMPLATE_ORIGINAL_THEME_ID
        if service is not None:
            for theme in service.all_themes():
                self.export_style.addItem(theme.name, theme.theme_id)
            active = service.active_theme_id()
        index = self.export_style.findData(active)
        self.export_style.setCurrentIndex(max(index, 0))
        self.export_style.blockSignals(False)
        visible = service is not None
        for widget in (
            self.export_style_label,
            self.export_style,
            self.edit_style_button,
        ):
            widget.setVisible(visible)

    def get_style_id(self) -> str:
        return self.export_style.currentData() or TEMPLATE_ORIGINAL_THEME_ID

    def get_style_name(self) -> str:
        return self.export_style.currentText() or ORIGINAL_THEME_NAME

    def _on_style_changed(self, index: int):
        theme_id = self.export_style.itemData(index)
        service = self._theme_service()
        if theme_id is None or service is None:
            return
        service.set_active(theme_id)
        self.style_changed.emit(theme_id)

    def _on_format_changed(self, index: int):
        fmt = self.export_format.currentData()
        if fmt:
            add_update_setting_value(EXPORT_FORMAT_SETTING_KEY, fmt)

    def set_export_location(self):
        _folder = QFileDialog.getExistingDirectory(
            self,
            caption="Select your location to export diagrams to",
            dir=os.path.join(install_root()),
        )

        if _folder:
            self.store_export_location(_folder)
            self.export_path_changed.emit()


if __name__ == "__main__":
    # Setup UI and begin thread
    app = QApplication(sys.argv)
    window = ExportSettings()
    window.show()

    app.exec()
