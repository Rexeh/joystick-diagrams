import logging
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QPushButton,
    QTreeWidgetItem,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.ui.qt_designer import setting_page_ui

_logger = logging.getLogger(__name__)


class PluginsPage(
    QMainWindow, setting_page_ui.Ui_Form
):  # Refactor pylint: disable=too-many-instance-attributes
    profileCollectionChange = Signal()

    pluginTreeChanged = Signal()
    togglePluginEnabledState = Signal(object)
    statistics_change = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Attributes
        self.plugin_count = 0
        self.plugins_ready = 0

        # Connections
        self.pluginTreeChanged.connect(self.update_plugin_count_statistics)
        self.runPluginsButton.clicked.connect(self.call_plugin_runner)
        self.togglePluginEnabledState.connect(self.toggle_enabled_plugin)

        self.statistics_change.connect(self.update_run_button_state)

        # self.parserPluginList.itemClicked.connect(self.plugin_selected)
        # self.parserPluginList.itemChanged.connect(self.plugin_selected)
        self.profileCollectionChange.connect(self.update_profile_collections)

        # Setup
        # self.pageTitle.setText("Available plugins")
        self.remove_defaults()
        self.populate_available_plugin_list()

        # Header Column Setup
        self.plugin_header = QTreeWidgetItem()
        self.plugin_header.setText(0, "Plugin Name")
        self.plugin_header.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft)

        self.plugin_header.setText(1, "Enabled")

        self.plugin_header.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)

        self.plugin_header.setText(2, "Setup")
        self.plugin_header.setTextAlignment(2, Qt.AlignmentFlag.AlignLeft)

        self.plugin_header.setText(3, "Ready")
        self.plugin_header.setTextAlignment(3, Qt.AlignmentFlag.AlignHCenter)

        self.pluginTreeWidget.setColumnCount(4)

        self.pluginTreeWidget.setHeaderItem(self.plugin_header)
        self.pluginTreeWidget.setIconSize(QSize(30, 30))
        self.pluginTreeWidget.setWordWrap(False)

        self.pluginTreeWidget.header().setMinimumSectionSize(200)

        # Header Configuration
        self.pluginTreeWidget.header().setStretchLastSection(True)
        self.pluginTreeWidget.header().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.pluginTreeWidget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.pluginTreeWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )

        self.pluginTreeWidget.setProperty("class", "plugin-tree")

        # Styling Overrides
        self.installPlugin.setIcon(qta.icon("fa5s.file-import"))
        self.installPlugin.setToolTip("Available in future version")
        self.pluginTreeHelpLabel.setText(
            "Enable and setup the plugins you want to create diagrams for."
        )

    class EnabledPushButton(QPushButton):
        """Custom PushButton class to handle QTreeWidget item pass through to click event for embedded widget"""

        toggled = Signal(bool, object)

        def __init__(self, *args, row_data=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.row_data = row_data  # Custom data to be passed

        def mousePressEvent(self, event):
            self.toggle()
            self.toggled.emit(self.isChecked(), self.row_data)

    def update_run_button_state(self):
        self.runPluginsButton.setEnabled(False)

        if self.plugins_ready > 0:
            self.runPluginsButton.setText(f"Run {self.plugins_ready} plugins")
            self.runPluginsButton.setEnabled(True)
            self.runPluginsButton.setProperty("class", "run-button enabled")
        else:
            self.runPluginsButton.setText("No plugins ready")
            self.runPluginsButton.setProperty("class", "run-button disabled")

    def get_plugin_data_for_tree(self) -> list[PluginWrapper]:
        plugin_wrappers = []
        for plugin_row in range(self.pluginTreeWidget.topLevelItemCount()):
            plugin_data: PluginWrapper = self.pluginTreeWidget.topLevelItem(
                plugin_row
            ).data(0, Qt.ItemDataRole.UserRole)
            plugin_wrappers.append(plugin_data)

        return plugin_wrappers

    def update_plugin_count_statistics(self):
        plugin_item_count = self.pluginTreeWidget.topLevelItemCount()

        # Set Plugin Count
        self.plugin_count = plugin_item_count

        # Calculate Ready Plugins
        self.plugins_ready = 0
        for plugin in self.get_plugin_data_for_tree():
            if plugin.ready:
                self.plugins_ready = self.plugins_ready + 1
        self.statistics_change.emit()

    def remove_defaults(self):
        # self.parserPluginList.clear()
        pass

    def toggle_enabled_plugin(self, click_state: bool, data: QTreeWidgetItem):
        """Toggles an embedded enabled button from the QTreeWidgetItem

        This is overly complex but the only way I could come up with at the time
        """
        plugin_data: PluginWrapper = data.data(0, Qt.ItemDataRole.UserRole)
        plugin_data.enabled = click_state

        enabled_widget = self.pluginTreeWidget.itemWidget(data, 1)

        enabled_button_control = enabled_widget.findChild(self.EnabledPushButton)

        enabled_button_control.setText("Enabled" if click_state else "Disabled")
        self.populate_available_plugin_list()

    def generate_enabled_widget(
        self, state: bool, widget_item: QTreeWidgetItem
    ) -> tuple[QWidget, QPushButton]:
        widget = self.EnabledPushButton(row_data=widget_item)
        widget.setCheckable(True)
        widget.setText("Enabled" if state else "Disabled")
        widget.setChecked(state)
        widget.setProperty("class", "enabled-button")

        checkBoxWrapper = QWidget()
        checkBoxWrapper.setProperty("class", "enabled-wrapper")

        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(widget)
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)
        checkBoxWrapper.setLayout(layout)

        return (checkBoxWrapper, widget)

    def get_ready_state_icon(self, state: bool):
        button = QPushButton()
        button.setIconSize(QSize(25, 25))
        button.setFlat(True)
        button.setProperty("class", "ready-button")

        if state:
            button.setIcon(
                qta.icon("fa5s.check-circle", color="green", background="white")
            )
            return button

        button.setIcon(qta.icon("fa5s.times-circle", color="red"))
        return button

    def populate_available_plugin_list(self):
        self.pluginTreeWidget.clear()

        for plugin_data in self.appState.plugin_manager.plugin_wrappers:
            # Create base plugin row
            plugin = QTreeWidgetItem()

            # Set object to row
            plugin.setData(0, Qt.ItemDataRole.UserRole, plugin_data)

            # Set columns
            plugin.setText(0, f"{plugin_data.name} - V{plugin_data.version}")
            plugin.setIcon(0, QIcon(plugin_data.icon))

            # Add item to tree so it can be initlalised
            self.pluginTreeWidget.addTopLevelItem(plugin)

            # Setup further widgets on row

            ## Enabled State

            enabled_widget_wrapper, button = self.generate_enabled_widget(
                plugin_data.enabled, plugin
            )

            button.toggled.connect(self.toggle_enabled_plugin)

            self.pluginTreeWidget.setItemWidget(plugin, 1, enabled_widget_wrapper)

            ## Plugin Ready State
            self.pluginTreeWidget.setItemWidget(
                plugin, 3, self.get_ready_state_icon(plugin_data.ready)
            )
            plugin.setToolTip(
                3,
                "Plugin ready to use" if plugin_data.ready else plugin_data.error,
            )

            path_setup_button = QPushButton()
            path_setup_button.setProperty("class", "plugin-setup-button")
            path_setup_button.setText(
                "Setup plugin path" if not plugin_data.path else "Update plugin path"
            )
            path_setup_button.setStyleSheet("width:auto")
            path_setup_button.clicked.connect(self.handle_path_set_for_plugin)
            self.pluginTreeWidget.setItemWidget(plugin, 2, path_setup_button)

        self.pluginTreeChanged.emit()

    def get_plugin_path_type(
        self, plugin_wrapper: PluginWrapper
    ) -> PluginInterface.FilePath | PluginInterface.FolderPath:
        return plugin_wrapper.path_type

    def set_plugin_path(self, path: Path, plugin_wrapper: PluginWrapper) -> bool:
        if not isinstance(path, Path):
            _logger.error(
                f"Plugin path for {plugin_wrapper.plugin.name} was not a Path object"
            )
            return False

        try:
            _logger.debug(
                f"Atempting path set {path=} for plugin {plugin_wrapper.plugin.name}"
            )
            load = plugin_wrapper.set_path(path)

            if not load:
                _logger.error(
                    f"An error occured seting the {path=} for {plugin_wrapper.plugin.name}"
                )
                raise JoystickDiagramsError("Error loading plugin")
            if load:
                _logger.info(f"Path successfully set for {plugin_wrapper.plugin.name}")
                return True

        except JoystickDiagramsError:
            return False

    def handle_path_set_for_plugin(self) -> None:
        current_treewidget_row = self.pluginTreeWidget.currentItem()
        plugin_wrapper_object: PluginWrapper = current_treewidget_row.data(
            0, Qt.ItemDataRole.UserRole
        )

        new_path = self.open_file_dialog(plugin_wrapper_object)

        if not new_path:
            return

        path_set_state = self.set_plugin_path(new_path, plugin_wrapper_object)

        if path_set_state:
            self.pluginTreeWidget.setItemWidget(
                current_treewidget_row,
                3,
                self.get_ready_state_icon(plugin_wrapper_object.ready),
            )
        self.populate_available_plugin_list()
        self.pluginTreeChanged.emit()

    def open_file_dialog(self, plugin_object: PluginWrapper) -> Path | None:
        current_treewidget_row = self.pluginTreeWidget.currentItem()
        plugin_wrapper_object = current_treewidget_row.data(0, Qt.ItemDataRole.UserRole)

        plugin_path = self.get_plugin_path_type(plugin_wrapper_object)

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
                    return Path(_file[0])
            case PluginInterface.FolderPath:
                _folder = QFileDialog.getExistingDirectory(
                    self, plugin_path.dialog_title, plugin_path.default_path
                )
                if _folder:
                    return Path(_folder)
            case _:
                _logger.error("Unexpected plugin path type given.")

        return None

    def call_plugin_runner(self):
        for wrapper in self.get_plugin_data_for_tree():
            wrapper.process()

        self.profileCollectionChange.emit()

    @Slot()
    def update_profile_collections(self):
        _logger.debug("Updating profile collections from all plugins")
        self.appState.process_profiles_from_collections()


if __name__ == "__main__":
    pass
