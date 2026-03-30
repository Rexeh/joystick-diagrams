import logging
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.plugin_wrapper import PluginWrapper
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

        self.profileCollectionChange.connect(self.update_profile_collections)

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
        self.pluginTreeWidget.header().setMinimumSectionSize(130)
        self.pluginTreeWidget.header().setStretchLastSection(False)
        self.pluginTreeWidget.header().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.pluginTreeWidget.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
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
        self._current_worker: PluginExecutor | None = None

        self.populate_available_plugin_list()
        self.initialise_ui()

    class EnabledPushButton(QPushButton):
        """Custom PushButton class to handle QTreeWidget item pass through to click event for embedded widget"""

        toggled = Signal(bool, object)

        def __init__(self, *args, row_data=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.row_data = row_data

        def mousePressEvent(self, event):
            self.toggle()
            self.toggled.emit(self.isChecked(), self.row_data)

    def initialise_ui(self):
        """Used to restore state between window changes"""
        for plugin in self.get_plugin_data_for_tree():
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
        self.plugin_count = self.pluginTreeWidget.topLevelItemCount()
        self.plugins_ready = sum(
            1 for p in self.get_plugin_data_for_tree() if p.ready and p.enabled
        )
        self.statistics_change.emit()

    def toggle_enabled_plugin(self, click_state: bool, data: QTreeWidgetItem):
        """Toggles an embedded enabled button from the QTreeWidgetItem"""
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
            button.setIcon(qta.icon("fa5s.check-circle", color="#34D399"))
            return button

        button.setIcon(qta.icon("fa5s.times-circle", color="#EF4444"))
        return button

    def populate_available_plugin_list(self):
        self.pluginTreeWidget.clear()

        for plugin_data in self.appState.plugin_manager.plugin_wrappers:
            plugin = QTreeWidgetItem()
            plugin.setData(0, Qt.ItemDataRole.UserRole, plugin_data)

            plugin.setText(0, f"{plugin_data.name} - V{plugin_data.version}")
            plugin.setIcon(0, QIcon(plugin_data.icon))
            plugin.setText(4, "0")
            plugin.setTextAlignment(4, Qt.AlignmentFlag.AlignCenter)

            self.pluginTreeWidget.addTopLevelItem(plugin)

            enabled_widget_wrapper, button = self.generate_enabled_widget(
                plugin_data.enabled, plugin
            )
            button.toggled.connect(self.toggle_enabled_plugin)
            self.pluginTreeWidget.setItemWidget(plugin, 1, enabled_widget_wrapper)

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
                "Setup Plugin" if not plugin_data.ready else "Update Plugin"
            )
            path_setup_button.setChecked(plugin_data.ready)
            path_setup_button.clicked.connect(
                lambda checked, pw=plugin_data, btn=path_setup_button: (
                    btn.setChecked(pw.ready),
                    self.show_plugin_config_panel(pw),
                )
            )
            self.pluginTreeWidget.setItemWidget(plugin, 2, path_setup_button)

        self.pluginTreeChanged.emit()

    def show_plugin_config_panel(self, plugin_wrapper: PluginWrapper) -> None:
        """Show the configuration panel for a plugin in the side panel area."""
        self._clear_side_panel()
        panel = PluginConfigPanel(plugin_wrapper, self)
        panel.settings_changed.connect(self.populate_available_plugin_list)
        panel.close_requested.connect(self._clear_side_panel)
        self.treeWidgetSidePanel.addWidget(panel)

    def _clear_side_panel(self) -> None:
        while self.treeWidgetSidePanel.count():
            item = self.treeWidgetSidePanel.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def update_plugin_error_state(self, plugin: PluginWrapper):
        plugin_row = self.get_plugin_row_by_plugin_wrapper(plugin)
        if plugin_row is None:
            _logger.error(f"Plugin row was not found in plugins page for {plugin=}.")
            return
        plugin_row.setText(4, "An error occured")
        plugin_row.setToolTip(4, f"An error occured with the plugin: {plugin.error}")

    def get_plugin_row_by_plugin_wrapper(
        self, plugin_wrapper: PluginWrapper
    ) -> QTreeWidgetItem | None:
        search = self.pluginTreeWidget.findItems(
            plugin_wrapper.name, Qt.MatchFlag.MatchContains, 0
        )
        return search[0] if search else None

    def update_plugin_execute_state(self, plugin: PluginWrapper):
        """Locates a plugin in QTreeWidget based on the plugin object Name"""
        plugin_row = self.get_plugin_row_by_plugin_wrapper(plugin)
        if plugin_row is None:
            _logger.error(f"Plugin row was not found in plugins page for {plugin=}.")
            return
        plugin_collection_length = str(
            len(plugin.plugin_profile_collection)
            if plugin.plugin_profile_collection
            else 0
        )
        plugin_row.setText(4, plugin_collection_length)
        plugin_row.setToolTip(4, "")

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
        # Disable immediately to prevent a second run starting before the
        # thread's started signal arrives and disables the button.
        self.runPluginsButton.setDisabled(True)
        self.total_parsed_profiles.emit(0)

        # Keep a strong Python reference so GC doesn't collect the worker
        # (and its Signals QObject) while the thread is still running.
        self._current_worker = PluginExecutor(self.get_plugin_data_for_tree())
        self._current_worker.signals.started.connect(self.update_run_button_on_start)
        self._current_worker.signals.finished.connect(
            self.calculate_total_profile_count
        )
        self._current_worker.signals.finished.connect(self.update_run_button_on_finish)
        self._current_worker.signals.finished.connect(self.profileCollectionChange.emit)
        self._current_worker.signals.processed.connect(self.update_plugin_execute_state)
        self._current_worker.signals.process_error.connect(
            self.update_plugin_error_state
        )
        self.threadPool.start(self._current_worker)

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


class PluginConfigPanel(QWidget):
    """Side panel that shows all settings (including paths) for a single plugin.

    Opened when the user clicks Setup / Update Plugin in the tree.
    """

    settings_changed = Signal()
    close_requested = Signal()

    def __init__(self, plugin_wrapper: PluginWrapper, page: PluginsPage, parent=None):
        super().__init__(parent)
        self._wrapper = plugin_wrapper
        self._page = page
        self.setMinimumWidth(280)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        # --- Header row: icon + name + close button ---
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon(self._wrapper.icon).pixmap(QSize(24, 24)))
        icon_label.setFixedSize(24, 24)
        header_row.addWidget(icon_label)

        name_label = QLabel(self._wrapper.name)
        name_label.setFont(header_font)
        header_row.addWidget(name_label, stretch=1)

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#9AA0A6"))
        close_btn.setIconSize(QSize(12, 12))
        close_btn.setFixedSize(24, 24)
        close_btn.setFlat(True)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: #2c2f38; border-radius: 4px; }"
        )
        close_btn.clicked.connect(self.close_requested.emit)
        header_row.addWidget(close_btn)
        outer.addLayout(header_row)

        version_label = QLabel(f"Version {self._wrapper.version}")
        outer.addWidget(version_label)

        outer.addWidget(self._make_separator())

        # --- All settings fields (paths and non-path) ---
        if self._wrapper.has_settings():
            path_fields = []
            other_fields = []

            for field_name, field_info in type(
                self._wrapper.plugin_settings
            ).model_fields.items():
                annotation = field_info.annotation
                is_path = annotation is Path or (
                    hasattr(annotation, "__args__") and Path in annotation.__args__
                )
                if is_path:
                    path_fields.append((field_name, field_info))
                else:
                    other_fields.append((field_name, field_info))

            if path_fields:
                path_heading = QLabel("Path" if len(path_fields) == 1 else "Paths")
                path_heading.setFont(self._section_font())
                outer.addWidget(path_heading)

                for field_name, field_info in path_fields:
                    current_value = getattr(self._wrapper.plugin_settings, field_name)
                    label_text = (
                        field_info.title or field_name.replace("_", " ").title()
                    )
                    tooltip = field_info.description or ""

                    lbl = QLabel(label_text)
                    lbl.setToolTip(tooltip)
                    outer.addWidget(lbl)

                    row = QHBoxLayout()
                    path_field = QLineEdit(str(current_value) if current_value else "")
                    path_field.setReadOnly(True)
                    path_field.setPlaceholderText("Not configured")
                    row.addWidget(path_field)

                    browse_btn = QPushButton("Browse...")
                    browse_btn.setFixedWidth(100)
                    browse_btn.clicked.connect(
                        lambda checked,
                        fn=field_name,
                        fi=field_info,
                        pf=path_field: self._on_path_browse(fn, fi, pf)
                    )
                    row.addWidget(browse_btn)
                    outer.addLayout(row)

            if other_fields:
                outer.addWidget(self._make_separator())
                settings_heading = QLabel("Settings")
                settings_heading.setFont(self._section_font())
                outer.addWidget(settings_heading)

                for field_name, field_info in other_fields:
                    current_value = getattr(self._wrapper.plugin_settings, field_name)
                    label_text = (
                        field_info.title or field_name.replace("_", " ").title()
                    )
                    tooltip = field_info.description or ""

                    row = QHBoxLayout()
                    lbl = QLabel(label_text)
                    lbl.setToolTip(tooltip)
                    row.addWidget(lbl, stretch=1)

                    widget = self._make_setting_widget(
                        field_name, field_info, current_value
                    )
                    if widget:
                        row.addWidget(widget)

                    outer.addLayout(row)

        outer.addStretch()

    # ------------------------------------------------------------------
    # Browse handler for Path fields
    # ------------------------------------------------------------------

    def _on_path_browse(
        self, field_name: str, field_info, path_field: QLineEdit
    ) -> None:
        extra = field_info.json_schema_extra or {}
        is_folder = extra.get("is_folder", True)
        default_path = str(Path(extra.get("default_path", "~")).expanduser())
        extensions = extra.get("extensions", [])

        if is_folder:
            result = QFileDialog.getExistingDirectory(
                self._page, field_info.title or "Select Folder", default_path
            )
            selected = Path(result) if result else None
        else:
            ext_filter = " ".join(f"*{e}" for e in extensions) if extensions else "*"
            result, _ = QFileDialog.getOpenFileName(
                self._page,
                field_info.title or "Select File",
                default_path,
                f"Files ({ext_filter})",
            )
            selected = Path(result) if result else None

        if selected is None:
            return

        try:
            self._wrapper.update_setting(field_name, selected)
            path_field.setText(str(selected))
            self.settings_changed.emit()
        except Exception as e:
            QMessageBox.warning(
                self._page,
                "Error",
                str(e),
                buttons=QMessageBox.StandardButton.Ok,
            )

    # ------------------------------------------------------------------
    # Widget factory for non-path settings
    # ------------------------------------------------------------------

    def _make_setting_widget(
        self, field_name: str, field_info, current_value
    ) -> QWidget | None:
        annotation = field_info.annotation

        if annotation is bool:
            widget = QCheckBox()
            widget.setChecked(bool(current_value))
            widget.stateChanged.connect(
                lambda state, k=field_name: self._on_setting_changed(k, bool(state))
            )
            return widget

        if annotation is str:
            extra = field_info.json_schema_extra or {}
            options = extra.get("options")
            if options:
                widget = QComboBox()
                widget.setProperty("class", "view-binds-list")
                for option in options:
                    widget.addItem(option)
                current_index = widget.findText(str(current_value or ""))
                if current_index >= 0:
                    widget.setCurrentIndex(current_index)
                widget.currentTextChanged.connect(
                    lambda text, k=field_name: self._on_setting_changed(k, text)
                )
                return widget

            widget = QLineEdit(str(current_value or ""))
            widget.editingFinished.connect(
                lambda k=field_name, w=widget: self._on_setting_changed(k, w.text())
            )
            return widget

        _logger.warning(f"No widget mapping for setting field type: {annotation}")
        return None

    def _on_setting_changed(self, key: str, value) -> None:
        self._wrapper.update_setting(key, value)
        self.settings_changed.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    @staticmethod
    def _section_font() -> QFont:
        font = QFont()
        font.setBold(True)
        return font


class Signals(QObject):
    started = Signal()
    processed = Signal(object)
    process_error = Signal(object)
    finished = Signal()


class PluginExecutor(QRunnable):
    """Executes parser plugins to run their process methods and produce ProfileCollections."""

    def __init__(self, plugin_wrappers: list[PluginWrapper]):
        super(PluginExecutor, self).__init__()
        self.plugin_wrappers = plugin_wrappers
        self.signals = Signals()

    @Slot()
    def run(self):
        self.signals.started.emit()

        for plugin in self.plugin_wrappers:
            if not plugin.enabled:
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
