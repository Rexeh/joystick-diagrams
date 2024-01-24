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
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.mock_main.qt_designer import setting_page_ui

_logger = logging.getLogger(__name__)


class PluginsPage(QMainWindow, setting_page_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    pluginPathSet = Signal(object)
    parsePlugins = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()
        self.remove_defaults()
        self.initialise_plugins_list()
        print(f"Plugins are: {self.appState.plugin_manager}")
        self.parserPluginList.itemClicked.connect(self.plugin_selected)
        self.pluginPathSet.connect(self.set_plugin_path)
        self.parsePlugins.connect(self.execute_plugin_parsers)

    def remove_defaults(self):
        self.parserPluginList.clear()

    def initialise_plugins_list(self):
        for plugin in self.appState.plugin_manager.get_available_plugins():
            item = QListWidgetItem(QIcon(plugin.icon), plugin.name)
            item.setData(Qt.UserRole, plugin)
            self.parserPluginList.addItem(item)

    @Slot()
    def plugin_selected(self, item):
        self.load_plugin_settings(self.get_selected_plugin_object())

    @Slot()
    def set_plugin_path(self, data):
        print(f"Data is {data}")
        try:
            currentPlugin = self.get_selected_plugin_object()
            success = currentPlugin.set_path(data)
            # TODO Plugin module needs improving to give better information?
            if success:
                self.parsePlugins.emit()
            else:
                QMessageBox.warning(
                    self,
                    "Plugin failure",
                    "Something went very wrong.",
                    buttons=QMessageBox.Discard,
                    defaultButton=QMessageBox.Discard,
                )
        except FileExistsError:  # Fix up
            print("Bang")

    @Slot()
    def execute_plugin_parsers(self):
        print("Executing plugin parsers")
        self.appState.process_loaded_plugins()

    def load_plugin_settings(self, data):
        self.pluginVersionInfo.setText(f"Version {data.version}")
        self.pluginName.setText(f"{data.name} Settings")

        # Path Setup
        self.pluginPath.setText(data.path)

        # Prevents duplicate signals from being connected
        if self.pluginPathButton.isSignalConnected(QMetaMethod.fromSignal(self.pluginPathButton.clicked)):
            self.pluginPathButton.clicked.disconnect()

        # Clean up
        # Additional validation to be added to PluginInterface/Plugin loading
        if isinstance(data.path_type, PluginInterface.FilePath):
            self.pluginPathButton.clicked.connect(lambda: self.file_dialog(data.path_type))

        if isinstance(data.path_type, PluginInterface.FolderPath):
            self.pluginPathButton.clicked.connect(lambda: self.folder_dialog(data.path_type))

    def get_selected_plugin_object(self) -> PluginInterface:
        return self.parserPluginList.currentItem().data(Qt.UserRole)

    def file_dialog(self, data) -> None:
        exts = " ".join(f"*{ext}" for ext in data.supported_extensions)

        _file = QFileDialog.getOpenFileName(
            self,
            caption=data.dialog_title,
            dir=data.default_path,
            filter=(f"All Files ({exts})"),
        )

        if _file[0]:
            self.pluginPathSet.emit(_file[0])

    def folder_dialog(self, data):
        _folder = QFileDialog.getExistingDirectory(self, data.dialog_title, data.default_path)

        if _folder:
            self.pluginPathSet.emit(_folder)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_init
    window = PluginsPage()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
