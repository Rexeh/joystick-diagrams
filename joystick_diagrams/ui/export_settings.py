import logging
import os
import sys

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

from joystick_diagrams.db.db_settings import add_update_setting_value, get_setting
from joystick_diagrams.ui.qt_designer import export_settings
from joystick_diagrams.utils import install_root

_logger = logging.getLogger(__name__)

EXPORT_PATH_SETTING_KEY = "export_path"
EXPORT_FORMAT_SETTING_KEY = "export_format"


class ExportSettings(QMainWindow, export_settings.Ui_Form):
    export_path_changed = Signal()

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
