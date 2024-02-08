import logging
import sys
from pathlib import Path

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox
from qt_material import apply_stylesheet

from joystick_diagrams import app_init
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.mock_main.qt_designer import plugin_settings_ui

_logger = logging.getLogger(__name__)

RECONFIGURE_TEXT = "Reconfigure"


class PluginSettings(
    QMainWindow, plugin_settings_ui.Ui_Form
):  # Refactor pylint: disable=too-many-instance-attributes
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
        self.pluginModified.connect(self.trigger_plugin_save)

        # Setup
        # Style Overrides

    def setup(self):
        """Initialise the widget configuration"""

        # Setup labels
        self.pluginEnabled.setChecked(self.plugin.enabled)
        self.plugin_name_label.setText(self.plugin.name)
        self.plugin_version_label.setText(self.plugin.version)

        # Setup file selection
        if self.plugin.path:
            self.configureLink.setText(RECONFIGURE_TEXT)
            self.configureLink.setDescription(self.plugin.path.__str__())
        else:
            self.configureLink.setText(self.get_plugin_path_type().dialog_title)
            self.configureLink.setDescription("")

    def handle_plugin_enabled_state(self):
        """Setup the plugin based on the enabled state. Only fully load enabled plugins for safety"""
        state = self.plugin.enabled

        match state:
            case 0:
                self.configureLink.setDisabled(1)

            case 1:
                self.configureLink.setDisabled(0)

            case _:
                self.configureLink.setDisabled(1)

    def trigger_plugin_save(self):
        self.plugin.store_plugin_configuration()

    @Slot()
    def handle_enabled_change(self, data):
        check_state = False if data == 0 else True
        # If the data is the same as the state do nothing
        if self.plugin.enabled == check_state:
            return

        # Set plugin state to new UI state
        self.plugin.enabled = data

        # Process based on the new state
        self.handle_plugin_enabled_state()

        _logger.debug(f"Plugin enabled state is now  {self.plugin.enabled}")

        self.pluginModified.emit(self.plugin)

    def get_plugin_path_type(
        self,
    ) -> PluginInterface.FilePath | PluginInterface.FolderPath:
        return self.plugin.path_type

    def set_plugin_path(self, path: Path):
        if not isinstance(path, Path):
            _logger.error(f"Plugin path for {self.plugin.name} was not a Path object")
            return

        try:
            _logger.debug(f"Atempting path set for plugin {self.plugin.name}")
            load = self.plugin.set_path(path)

            if not load:
                _logger.error(
                    f"An error occured seting the path for {self.plugin.name}"
                )
                raise JoystickDiagramsError("Error loading plugin")
            if load:
                _logger.info(f"Path successfully set for {self.plugin.name}")
                self.configureLink.setText(RECONFIGURE_TEXT)
                self.configureLink.setDescription(path.__str__())
                self.pluginPathConfigured.emit(self.plugin)
        except JoystickDiagramsError:
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
                _folder = QFileDialog.getExistingDirectory(
                    self, plugin_path.dialog_title, plugin_path.default_path
                )
                if _folder:
                    self.set_plugin_path(Path(_folder))
            case _:
                _logger.error("Unexpected plugin path type given.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init = app_init.init()
    window = PluginSettings()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
