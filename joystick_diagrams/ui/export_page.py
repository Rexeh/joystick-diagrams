import logging
import os
import webbrowser
from pathlib import Path

import qtawesome as qta  # type: ignore
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_device_management import (
    add_update_device_template_path,
)
from joystick_diagrams.db.db_settings import get_setting
from joystick_diagrams.export import export
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.plugins.output_plugin_interface import ExportResult
from joystick_diagrams.ui import main_window, ui_consts
from joystick_diagrams.ui.device_setup import DeviceSetup
from joystick_diagrams.ui.export_settings import ExportSettings
from joystick_diagrams.ui.qt_designer import export_ui
from joystick_diagrams.ui.widgets.section_header import SectionHeader
from joystick_diagrams.utils import install_root

_logger = logging.getLogger(__name__)


class ExportPage(QMainWindow, export_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Replace heading with SectionHeader
        self.heading_label.hide()
        self.section_header = SectionHeader(
            "fa5s.file-export",
            "Export",
            "Select devices, assign templates, and export your diagrams",
        )
        self.verticalLayout.insertWidget(0, self.section_header)

        self.ExportButton.clicked.connect(self.run_exporter)

        # Connections
        self.setTemplateButton.clicked.connect(self.select_template)

        # UI Setup
        self.setTemplateButton.setIconSize(QSize(20, 20))
        self.setTemplateButton.setIcon(
            qta.icon("fa5s.file-code", color="white", color_disabled="white")
        )
        self.setTemplateButton.setText("Select an item to set Template")
        self.setTemplateButton.setProperty("class", "template-set-button")

        self.setTemplateButton.setDisabled(True)

        self.ExportButton.setIcon(
            qta.icon("fa5s.file-export", color="white", color_disabled="white")
        )
        self.ExportButton.setProperty("class", "export-button")
        self.ExportButton.setIconSize(QSize(35, 35))

        # Include Device setup Widget
        self.device_widget = DeviceSetup()
        self.device_widget.device_item_selected.connect(self.change_template_button)
        self.devices_container.addWidget(self.device_widget)
        self.device_widget.number_of_selected_profiles.connect(
            self.update_export_button_state
        )

        # Double-click to set template on device tree
        self.device_widget.treeWidget.doubleClicked.connect(self._on_tree_double_click)

        self.device_header_label.setText("Devices")
        self.device_help_label.setText(
            "Choose your devices or profiles to export below. Double-click a device to assign a template."
        )

        ## Include Export Settings Panel
        self.export_settings_widget = ExportSettings()
        self.export_bottom_section.setProperty("class", "export-bottom-container")
        self.export_settings_container.setProperty("class", "export-settings-container")

        # Stack settings + output plugins row vertically within the container
        settings_stack = QVBoxLayout()
        settings_stack.setSpacing(4)
        settings_stack.setContentsMargins(0, 0, 0, 0)
        settings_stack.addWidget(self.export_settings_widget)

        # Output plugins — compact inline row matching export settings rows
        plugins_row = QHBoxLayout()
        plugins_row.setContentsMargins(0, 2, 0, 0)
        plugins_row.setSpacing(8)

        plugins_label = QLabel("Output Plugins")
        plugins_label.setStyleSheet("font-weight: bold;")
        plugins_row.addWidget(plugins_label)

        self._plugin_chips_layout = QHBoxLayout()
        self._plugin_chips_layout.setSpacing(6)
        self._plugin_chips_layout.setContentsMargins(0, 0, 0, 0)
        plugins_row.addLayout(self._plugin_chips_layout)
        plugins_row.addStretch()

        self._refresh_output_plugins_panel()
        settings_stack.addLayout(plugins_row)

        self.export_settings_container.addLayout(settings_stack)

        # Defaults
        self.update_export_button_state(0)  # Set the export button state

        # Threading pool
        self.threadPool = QThreadPool()

    def _make_plugin_chip(self, wrapper) -> QWidget:
        """Create a compact inline chip: status dot + name."""
        chip = QWidget()
        row = QHBoxLayout(chip)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        # Status dot: green if ready, amber if not configured
        dot_color = "#34D399" if wrapper.ready else "#F59E0B"
        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 3px;")
        row.addWidget(dot)

        name = QLabel(wrapper.name)
        name.setStyleSheet("color: #BDC1C6; font-size: 11px;")
        row.addWidget(name)

        status = "Ready" if wrapper.ready else "Not configured"
        chip.setToolTip(f"{wrapper.name} v{wrapper.version} — {status}")

        return chip

    def _refresh_output_plugins_panel(self):
        """Rebuild the plugin chips to reflect current enabled state."""
        while self._plugin_chips_layout.count():
            item = self._plugin_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        mgr = self.appState.output_plugin_manager
        enabled = mgr.get_enabled_plugin_wrappers() if mgr else []

        if not enabled:
            hint = QLabel("None active — enable in Settings")
            hint.setStyleSheet("color: #6B7280; font-size: 11px; font-style: italic;")
            self._plugin_chips_layout.addWidget(hint)
            return

        for wrapper in enabled:
            self._plugin_chips_layout.addWidget(self._make_plugin_chip(wrapper))

        self._plugin_chips_layout.addStretch()

    def refresh(self):
        """Refresh dynamic state when navigating back to this page."""
        self._refresh_output_plugins_panel()

    def _on_tree_double_click(self, index):
        """Handle double-click on device tree — trigger template selection for root items."""
        item = self.device_widget.treeWidget.currentItem()
        if item and item.parent() is None:
            self.select_template()

    def update_export_button_state(self, data: int):
        if data == 0:
            self.ExportButton.setDisabled(True)
            self.ExportButton.setText("  Select a profile to export")
            return

        self.ExportButton.setDisabled(False)

        profile_text = "profiles" if data > 1 else "profile"
        self.ExportButton.setText(f"  Export {data} {profile_text}")

    def change_template_button(self, data: QTreeWidgetItem):
        if data.parent():
            self.setTemplateButton.setDisabled(True)
            self.setTemplateButton.setText("Select an item to set Template")

        if data.parent() is None:
            self.setTemplateButton.setDisabled(False)
            self.setTemplateButton.setText(f"Update template for {data.text(0)}")

    def select_template(self):
        current_item = self.device_widget.treeWidget.currentItem()
        if not current_item or current_item.parent() is not None:
            return

        _file = QFileDialog.getOpenFileName(
            self,
            caption=f"Select an SVG file to use as a template - {current_item.text(0)}",
            filter=("SVG Files (*.svg)"),
            dir=os.path.join(install_root(), "templates"),
        )
        if _file[0]:
            file_path = Path(_file[0])
            self.set_template_for_device(file_path)

    def set_template_for_device(self, template_path: Path):
        selected_table_rows = self.device_widget.treeWidget.currentItem()

        # Selection Mode is single so force select first
        if not selected_table_rows:
            return  # Add handling here...

        # Not a root object, child was selected
        if selected_table_rows.parent() is not None:
            return

        row_guid_data = selected_table_rows.data(0, Qt.ItemDataRole.UserRole)

        # Save the device information
        _save = add_update_device_template_path(row_guid_data, str(template_path))

        if _save:
            self.device_widget.devices_updated.emit()

    def get_items_to_export(self) -> list[ExportDevice]:
        return self.device_widget.get_selected_export_items()

    def export_finished(self, data):
        # TODO handle MW interaction better
        main_window_inst: main_window = self.appState.main_window
        main_window_inst.progressBar.setRange(0, 100)
        main_window_inst.progressBar.setValue(0)
        main_window_inst.statusLabel.setText("Waiting...")

        msg_box = QMessageBox()
        msg_box.setWindowIcon(QIcon(ui_consts.JD_ICON))
        msg_box.setWindowTitle("Export Completed")
        msg_box.setText(
            f"{data} items were exported to {self.export_settings_widget.export_location}"
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        msg_box.exec()
        if get_setting("open_after_export") != "false":
            webbrowser.open(self.export_settings_widget.export_location)

    def update_export_progress(self, data):
        # TODO handle MW interaction better
        main_window_inst: main_window = self.appState.main_window
        main_window_inst.progressBar.setValue(data)
        main_window_inst.statusLabel.setText("Exporting templates")

    def _set_indeterminate_status(self, text: str):
        """Switch progress bar to indeterminate (barber pole) with a status message."""
        main_window_inst: main_window = self.appState.main_window
        main_window_inst.progressBar.setRange(0, 0)
        main_window_inst.statusLabel.setText(text)

    def show_export_error(self, message: str):
        QMessageBox.warning(
            self,
            "Export Error",
            message,
            buttons=QMessageBox.StandardButton.Ok,
            defaultButton=QMessageBox.StandardButton.Ok,
        )

    def unlock_export_button(self):
        self.ExportButton.setEnabled(True)

    def lock_export_button(self):
        self.ExportButton.setEnabled(False)

    def start_png_conversion(self, conversions: list):
        """Start converting SVGs to PNGs on the main thread using QWebEngineView."""
        from joystick_diagrams.export_image import PngConverter

        main_window_inst: main_window = self.appState.main_window
        main_window_inst.statusLabel.setText("Converting to PNG...")
        main_window_inst.progressBar.setValue(0)

        self._pending_export_count = len(conversions)
        # Extract ExportResult objects from the (svg, png, export_result) tuples
        self._pending_export_results = [t[2] for t in conversions if len(t) == 3]
        # Pass only (svg, png) pairs to PngConverter
        png_pairs = [(t[0], t[1]) for t in conversions]
        self._png_converter = PngConverter(png_pairs)
        self._png_converter.progress.connect(self._on_png_progress)
        self._png_converter.finished.connect(self._on_png_finished)
        self._png_converter.start()

    def _on_png_progress(self, current: int, total: int):
        main_window_inst: main_window = self.appState.main_window
        main_window_inst.progressBar.setValue(round(current / total * 100))

    def _on_png_finished(self):
        self._png_converter.deleteLater()
        self._png_converter = None

        export_results = getattr(self, "_pending_export_results", [])
        if export_results and self.appState.output_plugin_manager:
            self._set_indeterminate_status("Running output plugins...")
            output_worker = OutputPluginDispatch(export_results)
            output_worker.signals.finished.connect(self._finish_export)
            self.threadPool.start(output_worker)
        else:
            self._finish_export()

    def _finish_export(self):
        self.export_finished(self._pending_export_count)
        self.unlock_export_button()

    def run_exporter(self):
        # Check a location is set
        if self.export_settings_widget.export_location is None:
            QMessageBox.warning(
                self,
                "No export location set",
                "You need to set an export location before exporting",
                buttons=QMessageBox.StandardButton.Ok,
                defaultButton=QMessageBox.StandardButton.Ok,
            )
            return

        # Check what is selected / Child / Parent
        items_to_export = self.get_items_to_export()

        if not items_to_export:
            return

        # Export confirmation
        export_format = self.export_settings_widget.get_export_format()
        device_count = len(set(item.device_id for item in items_to_export))

        confirm_text = (
            f"Export {len(items_to_export)} profile{'s' if len(items_to_export) > 1 else ''} "
            f"across {device_count} device{'s' if device_count > 1 else ''} "
            f"as {export_format} to:\n\n{self.export_settings_widget.export_location}"
        )

        # Mention active output plugins
        mgr = self.appState.output_plugin_manager
        if mgr:
            enabled = mgr.get_enabled_plugin_wrappers()
            if enabled:
                names = ", ".join(w.name for w in enabled)
                confirm_text += f"\n\nOutput plugins: {names}"

        reply = QMessageBox.question(
            self,
            "Confirm Export",
            confirm_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        worker = ExportDispatch(
            items_to_export, self.export_settings_widget.export_location, export_format
        )

        worker.signals.started.connect(self.lock_export_button)
        worker.signals.finished.connect(self.export_finished)
        worker.signals.finished.connect(self.unlock_export_button)
        worker.signals.progress.connect(self.update_export_progress)
        worker.signals.status_update.connect(self._set_indeterminate_status)
        worker.signals.error.connect(self.show_export_error)
        worker.signals.png_conversion_needed.connect(self.start_png_conversion)
        self._pending_export_count = 0
        self.threadPool.start(worker)


class ExportSignals(QObject):
    started = Signal()
    finished = Signal(int)
    progress = Signal(int)
    error = Signal(str)
    status_update = Signal(str)
    png_conversion_needed = Signal(
        list
    )  # list of (svg_path, png_path, ExportResult) tuples


class OutputPluginSignals(QObject):
    finished = Signal()


class OutputPluginDispatch(QRunnable):
    """Runs enabled output plugins after PNG conversion completes."""

    def __init__(self, results: list):
        super().__init__()
        self.results = results
        self.signals = OutputPluginSignals()

    @Slot()
    def run(self):
        app_state = AppState()
        if app_state.output_plugin_manager:
            for (
                wrapper
            ) in app_state.output_plugin_manager.get_enabled_plugin_wrappers():
                try:
                    wrapper.run(self.results)
                except Exception as e:
                    _logger.error(
                        f"Output plugin '{wrapper.name}' raised an exception: {e}"
                    )
        self.signals.finished.emit()


class ExportDispatch(QRunnable):
    """
    ExportDispatch
    Exports items out to files

    """

    def __init__(
        self,
        export_items: list[ExportDevice],
        export_directory: str,
        export_format: str = "SVG",
        **kwargs,
    ):
        super(ExportDispatch, self).__init__()

        self.export_items = export_items
        self.export_directory = export_directory
        self.export_format = export_format
        self.signals = ExportSignals()

    @Slot()  # QtCore.Slot
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        self.signals.started.emit()
        item_count = len(self.export_items)

        # Export SVG files (always generates SVGs; for PNG, conversion is post-processed)
        exported_count = 0
        png_conversions = []
        export_results = []

        for count, item in enumerate(self.export_items, 1):
            _logger.info(
                f"Exporting {count}/{item_count} which has profile {item.profile_wrapper.profile_name}"
            )
            try:
                result = export(item, self.export_directory, self.export_format)
                exported_count += 1

                if result is not None:
                    svg_path, png_path = result
                    is_png = png_path is not None

                    export_result = ExportResult(
                        profile_name=item.profile_wrapper.profile_name,
                        device_name=item.device_name,
                        device_guid=item.device_id,
                        source_plugin=item.profile_wrapper.profile_origin.name,
                        template_name=item.template_file_name,
                        export_format="PNG" if is_png else "SVG",
                        file_path=Path(png_path if is_png else svg_path),
                        export_directory=Path(self.export_directory),
                        device=item.device,
                    )
                    export_results.append(export_result)

                    if is_png:
                        png_conversions.append((svg_path, png_path, export_result))

            except PermissionError:
                self.signals.error.emit(
                    f"Permission denied writing to '{self.export_directory}'. "
                    f"Choose a different export location or check folder permissions."
                )
                self.signals.finished.emit(exported_count)
                return
            except Exception as e:
                _logger.error(
                    f"Failed to export {item.profile_wrapper.profile_name}: {e}"
                )
                self.signals.error.emit(
                    f"Failed to export {item.profile_wrapper.profile_name}: {e}"
                )

            self.signals.progress.emit(
                round(count / item_count * 100 if item != item_count - 1 else 100)
            )

        # After SVG export, call plugin export methods if they exist
        self._call_plugin_exports()

        # If PNG format, signal main thread to do the conversion + output plugins after
        if png_conversions:
            self.signals.png_conversion_needed.emit(png_conversions)
        else:
            # SVG format: dispatch output plugins directly on this worker thread
            if export_results:
                self.signals.status_update.emit("Running output plugins...")
            self._dispatch_output_plugins(export_results)
            self.signals.finished.emit(exported_count)

    def _call_plugin_exports(self):
        """Call export_mappings method on plugins that implement it"""
        try:
            appState = AppState()

            # Get enabled plugins that have export functionality
            plugins_with_export = [
                pw
                for pw in appState.plugin_manager.get_enabled_plugin_wrappers()
                if hasattr(pw.plugin, "export_mappings")
            ]

            if not plugins_with_export:
                return

            self.signals.status_update.emit("Running plugin exports...")

            for plugin_wrapper in plugins_with_export:
                try:
                    _logger.info(f"Calling export for plugin: {plugin_wrapper.name}")
                    export_path = Path(self.export_directory)
                    success = plugin_wrapper.plugin.export_mappings(export_path)
                    if success:
                        _logger.info(
                            f"Successfully exported data for plugin: {plugin_wrapper.name}"
                        )
                    else:
                        _logger.warning(
                            f"Export failed for plugin: {plugin_wrapper.name}"
                        )
                except Exception as e:
                    _logger.error(
                        f"Error during export for plugin {plugin_wrapper.name}: {e}"
                    )

        except Exception as e:
            _logger.error(f"Error accessing plugin manager for exports: {e}")

    def _dispatch_output_plugins(self, results: list):
        """Run enabled output plugins with the given export results."""
        if not results:
            return
        try:
            app_state = AppState()
            if app_state.output_plugin_manager:
                for (
                    wrapper
                ) in app_state.output_plugin_manager.get_enabled_plugin_wrappers():
                    try:
                        wrapper.run(results)
                    except Exception as e:
                        _logger.error(
                            f"Output plugin '{wrapper.name}' raised an exception: {e}"
                        )
        except Exception as e:
            _logger.error(f"Error dispatching output plugins: {e}")


if __name__ == "__main__":
    pass
