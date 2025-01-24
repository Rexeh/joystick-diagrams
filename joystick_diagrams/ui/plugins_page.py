import logging
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal, Slot
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


class PluginsPage(QMainWindow, setting_page_ui.Ui_Form):
    profileCollectionChange = Signal()
    pluginTreeChanged = Signal()
    togglePluginEnabledState = Signal(object)
    statistics_change = Signal()
    total_parsed_profiles = Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Attributes
        self.plugin_count = 0
        self.plugins_ready = 0

        # Connections
        self.pluginTreeChanged.connect(self.update_plugin_count_statistics)
        self.pluginTreeChanged.connect(self.initialise_ui)

        self.runPluginsButton.clicked.connect(self.call_plugin_runner)
        self.togglePluginEnabledState.connect(self.toggle_enabled_plugin)

        self.statistics_change.connect(self.update_run_button_state)

        # self.parserPluginList.itemClicked.connect(self.plugin_selected)
        # self.parserPluginList.itemChanged.connect(self.plugin_selected)
        self.profileCollectionChange.connect(self.update_profile_collections)

        # Setup

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

        self.plugin_header.setText(4, "Profiles")
        self.plugin_header.setTextAlignment(4, Qt.AlignmentFlag.AlignHCenter)

        self.pluginTreeWidget.setColumnCount(5)

        self.pluginTreeWidget.setHeaderItem(self.plugin_header)
        self.pluginTreeWidget.setIconSize(QSize(30, 30))
        self.pluginTreeWidget.setWordWrap(False)
        self.pluginTreeWidget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

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
            "Enable and setup the plugins you want to create diagrams for. Run the plugins when ready to begin."
        )

        self.runPluginsButton.setProperty("class", "run-button")

        self.threadPool = QThreadPool()

        self.populate_available_plugin_list()
        self.initialise_ui()

    class EnabledPushButton(QPushButton):
        """Custom PushButton class to handle QTreeWidget item pass through to click event for embedded widget"""

        toggled = Signal(bool, object)

        def __init__(self, *args, row_data=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.row_data = row_data  # Custom data to be passed

        def mousePressEvent(self, event):
            self.toggle()
            self.toggled.emit(self.isChecked(), self.row_data)

    def initialise_ui(self):
        """Used to restore state between window changes"""
        plugins = self.get_plugin_data_for_tree()

        for plugin in plugins:
            self.update_plugin_execute_state(plugin)

    def update_run_button_state(self):
        self.runPluginsButton.setEnabled(False)

        if self.plugins_ready > 0:
            plugin_button_text = "plugins" if self.plugins_ready > 1 else "plugin"
            self.runPluginsButton.setText(
                f"Run {self.plugins_ready} {plugin_button_text}"
            )
            self.runPluginsButton.setEnabled(True)
        else:
            self.runPluginsButton.setText("No plugins ready")

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
            if plugin.ready and plugin.enabled:
                self.plugins_ready = self.plugins_ready + 1
        self.statistics_change.emit()

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

            plugin.setText(4, "0")
            plugin.setTextAlignment(4, Qt.AlignmentFlag.AlignCenter)

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
            path_setup_button.setCheckable(True)
            path_setup_button.setProperty("class", "plugin-setup-button")
            path_setup_button.setText(
                "Setup Plugin" if not plugin_data.path else "Update Plugin"
            )

            path_setup_button.setChecked(True if plugin_data.path else False)

            path_setup_button.clicked.connect(self.handle_path_set_for_plugin)
            self.pluginTreeWidget.setItemWidget(plugin, 2, path_setup_button)

        self.pluginTreeChanged.emit()

    def get_plugin_path_type(
        self, plugin_wrapper: PluginWrapper
    ) -> PluginInterface.FilePath | PluginInterface.FolderPath:
        return plugin_wrapper.path_type

    def get_plugin_row_by_plugin_wrapper(
        self, plugin_wrapper: PluginWrapper
    ) -> QTreeWidgetItem | None:
        search = self.pluginTreeWidget.findItems(
            plugin_wrapper.name, Qt.MatchFlag.MatchContains, 0
        )
        return search[0] if search else None

    def update_plugin_error_state(self, plugin: PluginWrapper):
        plugin_row: QTreeWidgetItem | None = self.get_plugin_row_by_plugin_wrapper(
            plugin
        )

        if plugin_row is None:
            _logger.error(
                f"Plugin row was not found in plugins  page for {plugin=}. This indicates a problem with UI state."
            )
            return

        plugin_row.setText(4, "An error occured")
        plugin_row.setToolTip(4, f"An error occured with the plugin: {plugin.error}")

    def update_plugin_execute_state(self, plugin: PluginWrapper):
        """Locates a plugin in QTreeWidget based on the plugin object Name"""

        plugin_row: QTreeWidgetItem | None = self.get_plugin_row_by_plugin_wrapper(
            plugin
        )

        if plugin_row is None:
            _logger.error(
                f"Plugin row was not found in plugins  page for {plugin=}. This indicates a problem with UI state."
            )
            return

        plugin_collection_length = str(
            len(plugin.plugin_profile_collection)
            if plugin.plugin_profile_collection
            else 0
        )

        plugin_row.setText(4, plugin_collection_length)
        plugin_row.setToolTip(4, "")

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
            # Handle Checked State NULL for exited
            widget: QPushButton = current_treewidget_row.treeWidget().itemWidget(
                current_treewidget_row, 2
            )

            widget.setChecked(not widget.isChecked())

            # widget.setChecked(widget.checkStateSet())
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
        plugin_path = self.get_plugin_path_type(plugin_object)

        match type(plugin_path):
            case PluginInterface.FilePath:
                exts = " ".join(f"*{ext}" for ext in plugin_path.supported_extensions)

                _file = QFileDialog.getOpenFileName(
                    self,
                    caption=plugin_path.dialog_title,
                    dir=str(plugin_path.default_path),
                    filter=(f"All Files ({exts})"),
                )

                if _file[0]:
                    return Path(_file[0])
            case PluginInterface.FolderPath:
                _folder = QFileDialog.getExistingDirectory(
                    self, plugin_path.dialog_title, str(plugin_path.default_path)
                )
                if _folder:
                    return Path(_folder)
            case _:
                _logger.error("Unexpected plugin path type given.")

        return None

    def update_run_button_on_start(self):
        animation = qta.Spin(self.runPluginsButton)
        spin_icon = qta.icon(
            "fa5s.spinner", color="white", color_active="white", animation=animation
        )
        self.runPluginsButton.setIconSize(QSize(35, 35))
        self.runPluginsButton.setIcon(spin_icon)
        self.runPluginsButton.setDisabled(True)

    def update_run_button_on_finish(self):
        self.runPluginsButton.setIcon(QIcon())
        self.runPluginsButton.setDisabled(False)

    def call_plugin_runner(self):
        # Emit parsed 0 to update buttons
        self.total_parsed_profiles.emit(0)

        worker = PluginExecutor(self.get_plugin_data_for_tree())

        # TODO handle started event/button disable

        worker.signals.started.connect(self.update_run_button_on_start)
        worker.signals.finished.connect(self.calculate_total_profile_count)
        worker.signals.finished.connect(self.update_run_button_on_finish)
        worker.signals.finished.connect(self.profileCollectionChange.emit)
        worker.signals.processed.connect(self.update_plugin_execute_state)
        worker.signals.process_error.connect(self.update_plugin_error_state)
        self.threadPool.start(worker)

    @Slot()
    def update_profile_collections(self):
        _logger.debug("Updating profile collections from all plugins")
        self.appState.process_profiles_from_collections()

    @Slot()
    def calculate_total_profile_count(self):
        count = sum(
            [
                len(x.plugin_profile_collection)
                for x in self.get_plugin_data_for_tree()
                if x.plugin_profile_collection
            ],
            0,
        )
        _logger.debug(f"Total of {count} profiles now detected")
        self.total_parsed_profiles.emit(count)


class Signals(QObject):
    started = Signal()
    processed = Signal(object)
    process_error = Signal(object)
    finished = Signal()


class PluginExecutor(QRunnable):
    """
    PluginExecutor
    Executes parser plugins to run their process methods and produce ProfileCollections

    """

    def __init__(self, plugin_wrappers: list[PluginWrapper]):
        super(PluginExecutor, self).__init__()
        # Store constructor arguments (re-used for processing)

        self.plugin_wrappers = plugin_wrappers
        self.signals = Signals()

    @Slot()  # QtCore.Slot
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        self.signals.started.emit()

        for plugin in self.plugin_wrappers:
            if not plugin.enabled:  # Added to prevent processing disabled plugins
                _logger.info(f"Plugin: {plugin.name} was disabled - skipping")
                continue

            process_state = plugin.process()

            if not process_state:
                _logger.error(f"An Exception Occured when processing {plugin.name}")
                self.signals.process_error.emit(plugin)
                break

            self.signals.processed.emit(plugin)

        self.signals.finished.emit()


if __name__ == "__main__":
    pass
