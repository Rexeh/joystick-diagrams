import logging
import sys
from pathlib import Path

from PySide6.QtCore import QDir, QMetaMethod, QObject, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QListWidgetItem, QMainWindow
from qt_material import apply_stylesheet

from joystick_diagrams import app_init
from joystick_diagrams.app_state import appState
from joystick_diagrams.plugin_manager import ParserPluginManager
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.mock_main import embed_UI
from joystick_diagrams.ui.mock_main.qt_designer import setting_page_ui

_logger = logging.getLogger(__name__)


class settingPage(QMainWindow, setting_page_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    pathTypeSignal = Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = appState()
        self.remove_defaults()
        self.initialise_plugins_list()
        print(f"Plugins are: {self.appState.plugin_manager}")
        self.parserPluginList.itemClicked.connect(self.plugin_selected)

    def remove_defaults(self):
        self.parserPluginList.clear()

    def initialise_plugins_list(self):
        for plugin in self.appState.plugin_manager.get_available_plugins():
            item = QListWidgetItem(QIcon(plugin.icon), plugin.name)
            item.setData(Qt.UserRole, plugin)
            self.parserPluginList.addItem(item)

    @Slot()
    def plugin_selected(self, item):
        self.load_plugin_settings(item.data(Qt.UserRole))

    def load_plugin_settings(self, data):
        self.pluginVersionInfo.setText(data.version)

        # Path Setup
        self.pluginPath.setText(data.path)

        # Prevents duplicate signals from being connected
        if self.pluginPathButton.isSignalConnected(QMetaMethod.fromSignal(self.pluginPathButton.clicked)):
            self.pluginPathButton.clicked.disconnect()

        # Clean up
        if isinstance(data.path_type, PluginInterface.FilePath):
            self.pluginPathButton.clicked.connect(lambda: self.file_dialog(data.path_type))

        if isinstance(data.path_type, PluginInterface.FolderPath):
            self.pluginPathButton.clicked.connect(lambda: self.folder_dialog(data.path_type))

    def file_dialog(self, data):
        exts = " ".join(f"*{ext}" for ext in data.supported_extensions)
        print(f"Default path is {data.default_path}")
        _file = QFileDialog.getOpenFileName(
            self,
            caption=data.dialog_title,
            dir=data.default_path,
            filter=(f"All Files ({exts})"),
        )
        print(_file)

    def folder_dialog(self, data):
        _folder = QFileDialog.getExistingDirectory(self, "Select Directory", data.default_path)
        print(_folder)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_init
    window = settingPage()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
