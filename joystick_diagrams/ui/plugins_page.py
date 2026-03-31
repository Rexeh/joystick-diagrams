import logging
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_settings import add_update_setting_value, get_setting
from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.ui.qt_designer import setting_page_ui
from joystick_diagrams.ui.widgets.section_header import SectionHeader

_logger = logging.getLogger(__name__)

SETUP_BANNER_DISMISSED_KEY = "setup_banner_dismissed"


class PluginsPage(QMainWindow, setting_page_ui.Ui_Form):
    profileCollectionChange = Signal()
    pluginListChanged = Signal()
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
        self._plugin_cards: list[PluginCard] = []

        # Replace the generated heading_label with SectionHeader
        self.heading_label.hide()
        self.section_header = SectionHeader(
            "fa5s.cog",
            "Plugin Setup",
            "Enable and configure your plugins, then run them to import bindings",
        )
        self.verticalLayout_2.insertWidget(0, self.section_header)

        # Hide the install plugin button and help label (replaced by SectionHeader subtitle)
        self.installPlugin.hide()
        self.pluginTreeHelpLabel.hide()
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)

        # Hide the old QTreeWidget — we replace it with plugin cards
        self.pluginTreeWidget.hide()

        # Create scrollable plugin cards area
        self._cards_scroll = QScrollArea()
        self._cards_scroll.setWidgetResizable(True)
        self._cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cards_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(6)
        self._cards_layout.addStretch()
        self._cards_scroll.setWidget(self._cards_container)

        # Insert the scroll area where the tree widget was
        self.pluginContainer.insertWidget(0, self._cards_scroll)

        # First-time guidance banner
        self._guidance_banner = None
        if not get_setting(SETUP_BANNER_DISMISSED_KEY):
            self._create_guidance_banner()

        # Connections
        self.pluginListChanged.connect(self.update_plugin_count_statistics)
        self.statistics_change.connect(self.update_run_button_state)
        self.profileCollectionChange.connect(self.update_profile_collections)

        # Run button styling and connection
        self.runPluginsButton.setProperty("class", "run-button")
        self.runPluginsButton.clicked.connect(self.call_plugin_runner)

        self.threadPool = QThreadPool()
        self._current_worker: PluginExecutor | None = None

        self.populate_plugin_cards()

    def _create_guidance_banner(self):
        """Create the first-time user guidance banner."""
        self._guidance_banner = QFrame()
        self._guidance_banner.setProperty("class", "guidance-banner")

        banner_layout = QHBoxLayout(self._guidance_banner)
        banner_layout.setContentsMargins(10, 8, 10, 8)
        banner_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon("fa5s.info-circle", color="#4C8BF5").pixmap(QSize(18, 18))
        )
        icon_label.setFixedSize(18, 18)
        banner_layout.addWidget(icon_label)

        text_label = QLabel(
            "Welcome! Enable a plugin below, configure its path, "
            "then click Run to import your bindings."
        )
        text_label.setWordWrap(True)
        banner_layout.addWidget(text_label, stretch=1)

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#9AA0A6"))
        close_btn.setIconSize(QSize(12, 12))
        close_btn.setFixedSize(20, 20)
        close_btn.setFlat(True)
        close_btn.setProperty("class", "guidance-banner-close")
        close_btn.clicked.connect(self._dismiss_guidance_banner)
        banner_layout.addWidget(close_btn)

        # Insert after section header
        self.verticalLayout_2.insertWidget(1, self._guidance_banner)

    def _dismiss_guidance_banner(self):
        if self._guidance_banner:
            self._guidance_banner.hide()
            add_update_setting_value(SETUP_BANNER_DISMISSED_KEY, "true")

    def update_run_button_state(self):
        self.runPluginsButton.setEnabled(False)
        self.runPluginsButton.setIcon(QIcon())

        if self.plugins_ready > 0:
            plugin_button_text = "plugins" if self.plugins_ready > 1 else "plugin"
            self.runPluginsButton.setText(
                f"  Run {self.plugins_ready} {plugin_button_text}"
            )
            self.runPluginsButton.setIcon(
                qta.icon("fa5s.play", color="white", color_disabled="#6B7280")
            )
            self.runPluginsButton.setIconSize(QSize(16, 16))
            self.runPluginsButton.setEnabled(True)
        else:
            self.runPluginsButton.setText("No plugins ready to run")

    def get_plugin_wrappers(self) -> list[PluginWrapper]:
        return [card.plugin_wrapper for card in self._plugin_cards]

    def update_plugin_count_statistics(self):
        self.plugin_count = len(self._plugin_cards)
        self.plugins_ready = sum(
            1 for p in self.get_plugin_wrappers() if p.ready and p.enabled
        )
        self.statistics_change.emit()

    def refresh(self):
        """Refresh plugin cards when returning to this page."""
        self.populate_plugin_cards()

    def populate_plugin_cards(self):
        """Build plugin card widgets from the plugin manager."""
        # Clear existing cards
        for card in self._plugin_cards:
            card.setParent(None)
            card.deleteLater()
        self._plugin_cards.clear()

        # Remove stretch
        while self._cards_layout.count():
            self._cards_layout.takeAt(0)

        for plugin_data in self.appState.plugin_manager.plugin_wrappers:
            card = PluginCard(plugin_data, self)
            card.enabled_toggled.connect(self._on_plugin_enabled_toggled)
            card.setup_clicked.connect(self.show_plugin_config_panel)
            self._plugin_cards.append(card)
            self._cards_layout.addWidget(card)

        self._cards_layout.addStretch()
        self.pluginListChanged.emit()
        self.update_run_button_state()

    def _on_plugin_enabled_toggled(self, plugin_wrapper: PluginWrapper, enabled: bool):
        plugin_wrapper.enabled = enabled
        self.update_plugin_count_statistics()

    def show_plugin_config_panel(self, plugin_wrapper: PluginWrapper) -> None:
        """Show the configuration panel for a plugin in the side panel area."""
        self._clear_side_panel()
        panel = PluginConfigPanel(plugin_wrapper, self)
        panel.settings_changed.connect(self._on_settings_changed)
        panel.close_requested.connect(self._clear_side_panel)
        self.treeWidgetSidePanel.addWidget(panel)

    def _on_settings_changed(self):
        """Refresh all cards when any plugin's settings change."""
        for card in self._plugin_cards:
            card.refresh_status()
        self.update_plugin_count_statistics()

    def _clear_side_panel(self) -> None:
        while self.treeWidgetSidePanel.count():
            item = self.treeWidgetSidePanel.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def update_plugin_error_state(self, plugin: PluginWrapper):
        for card in self._plugin_cards:
            if card.plugin_wrapper is plugin:
                card.set_error_state(plugin.error)
                break

    def update_plugin_execute_state(self, plugin: PluginWrapper):
        """Update a plugin card's profile count after execution."""
        for card in self._plugin_cards:
            if card.plugin_wrapper is plugin:
                count = (
                    len(plugin.plugin_profile_collection)
                    if plugin.plugin_profile_collection
                    else 0
                )
                card.set_profile_count(count)
                break

    def update_run_button_on_start(self):
        animation = qta.Spin(self.runPluginsButton)
        spin_icon = qta.icon(
            "fa5s.spinner", color="white", color_active="white", animation=animation
        )
        self.runPluginsButton.setIconSize(QSize(35, 35))
        self.runPluginsButton.setIcon(spin_icon)
        self.runPluginsButton.setText("  Running...")
        self.runPluginsButton.setDisabled(True)

    def update_run_button_on_finish(self):
        self.runPluginsButton.setIcon(QIcon())
        self.runPluginsButton.setDisabled(False)
        self.update_run_button_state()

    def call_plugin_runner(self):
        # Disable immediately to prevent a second run starting before the
        # thread's started signal arrives and disables the button.
        self.runPluginsButton.setDisabled(True)
        self.total_parsed_profiles.emit(0)

        # Keep a strong Python reference so GC doesn't collect the worker
        # (and its Signals QObject) while the thread is still running.
        self._current_worker = PluginExecutor(self.get_plugin_wrappers())
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
                for x in self.get_plugin_wrappers()
                if x.plugin_profile_collection
            ],
            0,
        )
        _logger.debug(f"Total of {count} profiles now detected")
        self.total_parsed_profiles.emit(count)


class PluginCard(QFrame):
    """A visual card representing a single plugin with status, enable toggle, and setup button."""

    enabled_toggled = Signal(object, bool)  # (PluginWrapper, enabled)
    setup_clicked = Signal(object)  # PluginWrapper

    def __init__(self, plugin_wrapper: PluginWrapper, parent=None):
        super().__init__(parent)
        self.plugin_wrapper = plugin_wrapper
        self._profile_count = 0
        self._build_ui()
        self.refresh_status()
        # Restore profile count from any previous plugin execution
        if plugin_wrapper.plugin_profile_collection:
            self.set_profile_count(len(plugin_wrapper.plugin_profile_collection))

    def _build_ui(self):
        self.setProperty("class", "plugin-card")
        self.setMinimumHeight(70)
        self.setMaximumHeight(90)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(14)

        # Left: Plugin icon
        icon_label = QLabel()
        icon_pixmap = QIcon(self.plugin_wrapper.icon).pixmap(QSize(42, 42))
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(42, 42)
        icon_label.setStyleSheet("background: transparent;")
        root.addWidget(icon_label)

        # Center: Name + version on top, status on bottom
        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(4)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_label = QLabel(self.plugin_wrapper.name)
        name_label.setProperty("class", "plugin-card-name")
        name_row.addWidget(name_label)

        version_label = QLabel(f"v{self.plugin_wrapper.version}")
        version_label.setProperty("class", "plugin-card-version")
        name_row.addWidget(version_label)
        name_row.addStretch()

        center.addLayout(name_row)

        # Status line
        self._status_layout = QHBoxLayout()
        self._status_layout.setContentsMargins(0, 0, 0, 0)
        self._status_layout.setSpacing(6)

        self._status_icon = QLabel()
        self._status_icon.setFixedSize(14, 14)
        self._status_icon.setStyleSheet("background: transparent;")
        self._status_layout.addWidget(self._status_icon)

        self._status_label = QLabel()
        self._status_label.setProperty("class", "plugin-card-status")
        self._status_layout.addWidget(self._status_label)
        self._status_layout.addStretch()

        center.addLayout(self._status_layout)
        root.addLayout(center, stretch=1)

        # Right: Profile count badge + Enabled toggle + Setup button
        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)

        # Profile count badge
        self._profile_badge = QLabel("0")
        self._profile_badge.setProperty("class", "profile-count-badge")
        self._profile_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._profile_badge.setFixedHeight(22)
        self._profile_badge.setMinimumWidth(28)
        self._profile_badge.setToolTip("Profiles parsed")
        self._profile_badge.hide()  # Hidden until profiles are parsed
        right.addWidget(self._profile_badge)

        # Enabled toggle
        self._enabled_btn = QPushButton(
            "Enabled" if self.plugin_wrapper.enabled else "Disabled"
        )
        self._enabled_btn.setCheckable(True)
        self._enabled_btn.setChecked(self.plugin_wrapper.enabled)
        self._enabled_btn.setProperty("class", "enabled-button")
        self._enabled_btn.clicked.connect(self._on_enabled_clicked)
        right.addWidget(self._enabled_btn)

        # Setup button
        self._setup_btn = QPushButton()
        self._setup_btn.setProperty("class", "plugin-setup-button")
        self._setup_btn.clicked.connect(
            lambda: self.setup_clicked.emit(self.plugin_wrapper)
        )
        right.addWidget(self._setup_btn)

        root.addLayout(right)

    def refresh_status(self):
        """Update the status indicator and card accent based on current plugin state."""
        pw = self.plugin_wrapper

        if pw.error:
            self._set_status("error", pw.error, "fa5s.times-circle", "#EF4444")
            self._update_card_class("error")
        elif pw.ready:
            self._set_status("ready", "Ready", "fa5s.check-circle", "#34D399")
            self._update_card_class("ready")
        else:
            msg = pw.error or "Not configured"
            self._set_status("not-ready", msg, "fa5s.exclamation-circle", "#F59E0B")
            self._update_card_class("not-ready")

        self._setup_btn.setText("Update" if pw.ready else "Setup")

    def _set_status(self, css_class: str, text: str, icon_name: str, color: str):
        self._status_icon.setPixmap(
            qta.icon(icon_name, color=color).pixmap(QSize(14, 14))
        )
        self._status_label.setText(text)
        self._status_label.setProperty("class", f"plugin-card-status {css_class}")
        # Force style refresh
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _update_card_class(self, state: str):
        self.setProperty("class", f"plugin-card {state}")
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_enabled_clicked(self, checked: bool):
        self._enabled_btn.setText("Enabled" if checked else "Disabled")
        self.enabled_toggled.emit(self.plugin_wrapper, checked)

    def set_profile_count(self, count: int):
        self._profile_count = count
        self._profile_badge.setText(str(count))
        self._profile_badge.setVisible(count > 0)
        self._profile_badge.setToolTip(
            f"{count} profile{'s' if count != 1 else ''} parsed"
        )

    def set_error_state(self, error_message: str | None):
        self._set_status(
            "error",
            error_message or "An error occurred",
            "fa5s.times-circle",
            "#EF4444",
        )
        self._update_card_class("error")


class PluginConfigPanel(QWidget):
    """Side panel that shows all settings (including paths) for a single plugin.

    Opened when the user clicks Setup / Update Plugin in a card.
    """

    settings_changed = Signal()
    close_requested = Signal()

    def __init__(self, plugin_wrapper: PluginWrapper, page: PluginsPage, parent=None):
        super().__init__(parent)
        self._wrapper = plugin_wrapper
        self._page = page
        self.setMinimumWidth(280)
        self.setFixedWidth(350)
        self.setProperty("class", "plugin-config-panel")
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 14, 14)
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
            "QPushButton:hover { background: #3C4043; border-radius: 4px; }"
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
