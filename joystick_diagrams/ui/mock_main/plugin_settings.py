import logging
import sys
from pathlib import Path

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
from joystick_diagrams.exceptions import JoystickDiagramsException
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.mock_main.qt_designer import plugin_settings_ui
from joystick_diagrams.ui.plugin_wrapper import PluginWrapper

_logger = logging.getLogger(__name__)

RECONFIGURE_TEXT = "Reconfigure"


class PluginSettings(QMainWindow, plugin_settings_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    pluginModified = Signal(object)
    pluginPathConfigured = Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.plugin = None

        # Attributes

        # Connections
        self.pluginEnabled.stateChanged.connect(self.handle_enabled_change)
        self.configureLink.clicked.connect(self.open_file_dialog)

        # Setup

        # Style Overrides
        self.configureLink.setStyleSheet("color: white !important;")

    def setup(self):
        """Initialise the widget configuration"""

        # Setup labels
        self.pluginEnabled.setChecked(self.plugin.enabled)
        self.plugin_name_label.setText(self.plugin.plugin_name)
        self.plugin_version_label.setText(self.plugin.plugin_version)

        # Setup file selection
        self.configureLink.setText(self.get_plugin_path_type().dialog_title)
        self.configureLink.setDescription("")

        if self.plugin.plugin.path:
            self.set_plugin_path(self.plugin.plugin.path)

        # TODO if file already set from storage...

    def handle_enabled_change(self, data):
        self.plugin.enabled = data if data == 0 else 1
        print(f"Plugin enabled state is now  {self.plugin.enabled}")
        self.pluginModified.emit(self.plugin)

    def get_plugin_file_extensions(self):
        return []

    def get_plugin_path_type(self) -> PluginInterface.FilePath | PluginInterface.FolderPath:
        return self.plugin.plugin.path_type

    def set_plugin_path(self, path: Path):
        if not isinstance(path, Path):
            return

        try:
            load = self.plugin.plugin.set_path(path)

            if not load:
                raise JoystickDiagramsException("Error loading plugin")
            if load:
                self.configureLink.setText(RECONFIGURE_TEXT)
                self.configureLink.setDescription(path.__str__())
                self.pluginPathConfigured.emit(self.plugin)
        except JoystickDiagramsException:
            QMessageBox.warning(
                self,
                "Plugin failure",
                "Something went very wrong.",
                buttons=QMessageBox.Discard,
                defaultButton=QMessageBox.Discard,
            )

    def open_file_dialog(self) -> None:
        plugin_path = self.get_plugin_path_type()

        match type(plugin_path):
            case PluginInterface.FilePath:
                exts = " ".join(f"*{ext}" for ext in plugin_path.supported_extensions)

                _file = QFileDialog.getOpenFileName(
                    self,
                    caption=plugin_path.dialog_title,
                    dir=plugin_path.default_path,
                    filter=(f"All Files ({exts})"),
                )

                if _file[0]:
                    self.set_plugin_path(Path(_file[0]))
            case PluginInterface.FolderPath:
                _folder = QFileDialog.getExistingDirectory(self, plugin_path.dialog_title, plugin_path.default_path)
                if _folder:
                    self.set_plugin_path(Path(_folder))
            case _:
                _logger.error("Unexpected plugin path type given.")

    # def load_plugin_settings(self, data):


#     self.pluginVersionInfo.setText(f"Version {data.version}")
#     self.pluginName.setText(f"{data.name} Settings")

#     # Path Setup
#     self.pluginPath.setText(data.path)

#     # Prevents duplicate signals from being connected
#     if self.pluginPathButton.isSignalConnected(QMetaMethod.fromSignal(self.pluginPathButton.clicked)):
#         self.pluginPathButton.clicked.disconnect()

#     # Clean up
#     # Additional validation to be added to PluginInterface/Plugin loading
#     if isinstance(data.path_type, PluginInterface.FilePath):
#         self.pluginPathButton.clicked.connect(lambda: self.file_dialog(data.path_type))

#     if isinstance(data.path_type, PluginInterface.FolderPath):
#         self.pluginPathButton.clicked.connect(lambda: self.folder_dialog(data.path_type))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init = app_init.init()
    window = PluginSettings()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
