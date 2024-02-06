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
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.mock_main.plugin_settings import PluginSettings
from joystick_diagrams.ui.mock_main.qt_designer import setting_page_ui
from joystick_diagrams.ui.plugin_wrapper import PluginWrapper

_logger = logging.getLogger(__name__)


class PluginsPage(QMainWindow, setting_page_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    profileCollectionChange = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Attributes
        self.plugin_wrappers: list[PluginWrapper] = []
        self.window_content = None

        # Connections
        self.parserPluginList.itemClicked.connect(self.plugin_selected)
        self.parserPluginList.itemChanged.connect(self.plugin_selected)
        self.profileCollectionChange.connect(self.update_profile_collections)

        # Setup
        self.remove_defaults()
        self.initialise_plugins()
        self.populate_available_plugin_list()

        # Styling Overrides

    def remove_defaults(self):
        self.parserPluginList.clear()

    def initialise_plugins(self):
        """Initialise the available plugins into wrapper objects for use in UI.

        PluginWrapper enriches the Plugin model with UI specific data
        """
        for plugin in self.appState.plugin_manager.get_available_plugins():

            self.plugin_wrappers.append(PluginWrapper(plugin))

    def populate_available_plugin_list(self):
        for plugin_data in self.plugin_wrappers:
            item = QListWidgetItem(QIcon(plugin_data.icon), plugin_data.name)
            item.setData(Qt.UserRole, plugin_data)
            self.parserPluginList.addItem(item)

        self.pre_intiialise_plugin_wrappers()

    def pre_intiialise_plugin_wrappers(self):
        """Sets up the wrappers in the UI, so that users don't need to click on them individually

        This could be done better but for now it works
        """
        for item in range(self.parserPluginList.count()):
            self.parserPluginList.setCurrentRow(item)
            self.plugin_selected()

    @Slot()
    def plugin_selected(self):
        if self.window_content:
            self.window_content.hide()

        self.window_content = PluginSettings()

        # Signals/Slots
        self.window_content.pluginPathConfigured.connect(self.handle_plugin_path_load)

        # Page Setup For now
        self.window_content.plugin = self.get_selected_plugin_object()

        self.window_content.setup()

        self.window_content.setParent(self.pluginOptionsWidget)
        self.window_content.show()

    @Slot()
    def handle_plugin_path_load(self, plugin: PluginWrapper):
        _logger.debug(f"Plugin path changed for {plugin}, attempting to process plugin")
        try:
            plugin.plugin_profile_collection = plugin.plugin.process()
            self.profileCollectionChange.emit()
        except JoystickDiagramsException:
            pass

    def get_plugin_wrapper_collections(self) -> dict[str, ProfileCollection]:
        """Returns a list of Profile Collections that are tagged with the Plugin Name where the plugin is enabled"""
        return {
            x.name: x.plugin_profile_collection
            for x in self.plugin_wrappers
            if x.enabled and x.plugin_profile_collection
        }

    @Slot()
    def update_profile_collections(self):
        _logger.debug(f"Updating profile collections from all plugins")
        self.appState.process_loaded_plugins(self.get_plugin_wrapper_collections())

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
