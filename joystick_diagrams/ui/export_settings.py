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


class ExportSettings(QMainWindow, export_settings.Ui_Form):
    export_path_changed = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        # Attributes
        self.export_location = None

        # Connections
        self.setExportLocationButton.clicked.connect(self.set_export_location)
        self.export_path_changed.connect(self.setup_widget)

        # Setup
        self.setup_widget()

        # Styling Overrides

    def setup_widget(self):
        export_location = self.get_export_location()

        if export_location:
            self.export_location_label.setText(export_location)
            self.setExportLocationButton.setText("Change Export Location")
            self.export_location = export_location
            return

        self.export_location_label.setText("Not Selected")
        self.setExportLocationButton.setText("Set Export Location")

    def get_export_location(self):
        """Gets the stored export location if available"""
        return get_setting(EXPORT_PATH_SETTING_KEY)

    def store_export_location(self, location: str):
        add_update_setting_value(EXPORT_PATH_SETTING_KEY, location)

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
