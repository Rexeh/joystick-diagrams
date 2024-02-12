import logging

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QListWidgetItem, QMainWindow

from joystick_diagrams.app_state import AppState
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.plugin_settings import PluginSettings
from joystick_diagrams.ui.qt_designer import setting_page_ui

_logger = logging.getLogger(__name__)


class PluginsPage(
    QMainWindow, setting_page_ui.Ui_Form
):  # Refactor pylint: disable=too-many-instance-attributes
    profileCollectionChange = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Attributes
        self.window_content = None

        # Connections
        self.parserPluginList.itemClicked.connect(self.plugin_selected)
        self.parserPluginList.itemChanged.connect(self.plugin_selected)
        self.profileCollectionChange.connect(self.update_profile_collections)

        # Setup
        self.pageTitle.setText("Available plugins")
        self.remove_defaults()
        self.populate_available_plugin_list()

        # Styling Overrides

    def remove_defaults(self):
        self.parserPluginList.clear()

    def populate_available_plugin_list(self):
        for plugin_data in self.appState.plugin_manager.plugin_wrappers:
            item = QListWidgetItem(QIcon(plugin_data.icon), plugin_data.name)
            item.setData(Qt.ItemDataRole.UserRole, plugin_data)
            self.parserPluginList.addItem(item)

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

        self.window_content.setParent(self.pluginOptionWidget)
        self.window_content.show()

    @Slot()
    def handle_plugin_path_load(self, plugin: PluginWrapper):
        _logger.debug(f"Plugin path changed for {plugin}, attempting to process plugin")
        try:
            plugin.process()
            self.profileCollectionChange.emit()
        except JoystickDiagramsError:
            pass

    @Slot()
    def update_profile_collections(self):
        _logger.debug("Updating profile collections from all plugins")
        self.appState.process_profile_collection_updates()

    def get_selected_plugin_object(self) -> PluginInterface:
        return self.parserPluginList.currentItem().data(Qt.ItemDataRole.UserRole)


if __name__ == "__main__":
    pass
