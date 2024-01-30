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
from joystick_diagrams.db import db_init, db_plugin_data
from joystick_diagrams.exceptions import JoystickDiagramsException
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.mock_main.plugin_settings import PluginSettings
from joystick_diagrams.ui.mock_main.qt_designer import setting_page_ui
from joystick_diagrams.ui.plugin_wrapper import PluginWrapper

_logger = logging.getLogger(__name__)


class PluginsPage(QMainWindow, setting_page_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    parsePlugins = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Attributes
        self.plugin_wrappers = []
        self.window_content = None

        # Connections
        self.parserPluginList.itemClicked.connect(self.plugin_selected)
        self.parsePlugins.connect(self.execute_plugin_parsers)

        # Setup
        self.remove_defaults()
        self.initialise_plugins()
        self.populate_available_plugin_list()

        # Styling Overrides

    def remove_defaults(self):
        self.parserPluginList.clear()

    def get_plugin_configuration(self, plugin_name: str):
        return db_plugin_data.get_plugin_configuration(plugin_name)

    @Slot()
    def store_plugin_configuration(self, plugin_object: PluginWrapper):
        db_plugin_data.add__update_plugin_configuration(plugin_object.plugin_name, plugin_object.enabled)

    def initialise_plugins(self):
        """Initialise the available plugins into wrapper objects for use in UI.

        PluginWrapper enriches the Plugin model with UI specific data
        """
        for plugin in self.appState.plugin_manager.get_available_plugins():
            plugin_lookup = self.get_plugin_configuration(plugin.name)

            if plugin_lookup:
                enabled_flag = plugin_lookup[1]
                self.plugin_wrappers.append(
                    PluginWrapper(plugin.name, plugin.version, plugin.icon, plugin, enabled=enabled_flag)
                )
            else:
                # Create Wrapper
                wrapper = PluginWrapper(plugin.name, plugin.version, plugin.icon, plugin, enabled=False)
                # Store the plugin with default of FALSE for enabled
                self.store_plugin_configuration(wrapper)

                self.plugin_wrappers.append(wrapper)

    def populate_available_plugin_list(self):
        for plugin_data in self.plugin_wrappers:
            item = QListWidgetItem(QIcon(plugin_data.plugin_icon), plugin_data.plugin_name)
            item.setData(Qt.UserRole, plugin_data)
            self.parserPluginList.addItem(item)

    @Slot()
    def plugin_selected(self, item):
        if self.window_content:
            self.window_content.hide()

        self.window_content = PluginSettings()

        # Page Setup For now
        self.window_content.plugin = self.get_selected_plugin_object()
        self.window_content.setup()

        # Signals/Slots
        self.window_content.pluginModified.connect(self.store_plugin_configuration)
        self.window_content.pluginPathConfigured.connect(self.handle_plugin_path_load)

        self.window_content.setParent(self.pluginOptionsWidget)
        self.window_content.show()

    @Slot()
    def handle_plugin_path_load(self, plugin: PluginWrapper):
        print(f"Data is {plugin}")
        try:
            plugin.plugin_profile_collection = plugin.plugin.process()
            print(f"Data is {plugin.plugin_profile_collection}")
        except JoystickDiagramsException:
            pass

    @Slot()
    def execute_plugin_parsers(self):
        print("Executing plugin parsers")
        self.appState.process_loaded_plugins()

    def get_selected_plugin_object(self) -> PluginInterface:
        return self.parserPluginList.currentItem().data(Qt.UserRole)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    db = db_init.init()
    init = app_init.init()
    window = PluginsPage()
    window.show()

    apply_stylesheet(app, theme="light_blue.xml", invert_secondary=True)
    app.exec()
