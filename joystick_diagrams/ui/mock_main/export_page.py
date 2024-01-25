import logging
import sys

from PySide6.QtCore import QMetaMethod, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
)
from qt_material import apply_stylesheet

from joystick_diagrams import app_init
from joystick_diagrams.app_state import AppState
from joystick_diagrams.export import export
from joystick_diagrams.ui.mock_main.qt_designer import export_ui

_logger = logging.getLogger(__name__)


class ExportPage(QMainWindow, export_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        self.ExportButton.clicked.connect(self.run_exporter)

    def run_exporter(self):
        for profile in self.appState.processedProfileObjectMapping.values():
            export(profile)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ExportPage()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
