import logging
import os
import webbrowser
from pathlib import Path

import qtawesome as qta  # type: ignore
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTreeWidgetItem

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_device_management import (
    add_update_device_template_path,
)
from joystick_diagrams.export import export
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.ui import main_window, ui_consts
from joystick_diagrams.ui.device_setup import DeviceSetup
from joystick_diagrams.ui.export_settings import ExportSettings
from joystick_diagrams.ui.qt_designer import export_ui
from joystick_diagrams.utils import install_root

_logger = logging.getLogger(__name__)


class ExportPage(QMainWindow, export_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()
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

        self.device_header_label.setText("Devices")
        self.device_help_label.setText(
            "Choose your devices or profiles to export below"
        )

        ## Include Export Settings Panel
        self.export_settings_widget = ExportSettings()
        self.export_settings_container.addWidget(self.export_settings_widget)
        self.export_bottom_section.setProperty("class", "export-bottom-container")
        self.export_settings_container.setProperty("class", "export-settings-container")

        # Defaults
        self.update_export_button_state(0)  # Set the export button state

        # Threading pool
        self.threadPool = QThreadPool()

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
        _file = QFileDialog.getOpenFileName(
            self,
            caption=f"Select an SVG file to use as a template - {self.device_widget.treeWidget.currentItem().text(0)}",
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
        webbrowser.open(self.export_settings_widget.export_location)

    def update_export_progress(self, data):
        # TODO handle MW interaction better
        main_window_inst: main_window = self.appState.main_window
        main_window_inst.progressBar.setValue(data)
        main_window_inst.statusLabel.setText("Exporting templates")

    def unlock_export_button(self):
        self.ExportButton.setEnabled(True)

    def lock_export_button(self):
        self.ExportButton.setEnabled(False)

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

        worker = ExportDispatch(
            items_to_export, self.export_settings_widget.export_location
        )

        worker.signals.started.connect(self.lock_export_button)
        worker.signals.finished.connect(self.export_finished)
        worker.signals.finished.connect(self.unlock_export_button)
        worker.signals.progress.connect(self.update_export_progress)
        self.threadPool.start(worker)


class ExportSignals(QObject):
    started = Signal()
    finished = Signal(int)
    progress = Signal(int)


class ExportDispatch(QRunnable):
    """
    ExportDispatch
    Exports items out to files

    """

    def __init__(
        self, export_items: list[ExportDevice], export_directory: str, **kwargs
    ):
        super(ExportDispatch, self).__init__()

        self.export_items = export_items
        self.export_directory = export_directory
        self.signals = ExportSignals()

    @Slot()  # QtCore.Slot
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        self.signals.started.emit()
        item_count = len(self.export_items)

        # Export SVG files first
        for count, item in enumerate(self.export_items, 1):
            _logger.info(
                f"Exporting {count}/{item_count} which has profile {item.profile_wrapper.profile_name}"
            )
            export(item, self.export_directory)

            self.signals.progress.emit(
                round(count / item_count * 100 if item != item_count - 1 else 100)
            )
        
        # After SVG export, call plugin export methods if they exist
        self._call_plugin_exports()
        
        self.signals.finished.emit(item_count)

    def _call_plugin_exports(self):
        """Call export_mappings method on plugins that implement it"""
        try:
            appState = AppState()
            
            # Get enabled plugins that have export functionality
            for plugin_wrapper in appState.plugin_manager.get_enabled_plugin_wrappers():
                if hasattr(plugin_wrapper.plugin, 'export_mappings'):
                    try:
                        _logger.info(f"Calling export for plugin: {plugin_wrapper.name}")
                        export_path = Path(self.export_directory)
                        success = plugin_wrapper.plugin.export_mappings(export_path)
                        if success:
                            _logger.info(f"Successfully exported data for plugin: {plugin_wrapper.name}")
                        else:
                            _logger.warning(f"Export failed for plugin: {plugin_wrapper.name}")
                    except Exception as e:
                        _logger.error(f"Error during export for plugin {plugin_wrapper.name}: {e}")
                        
        except Exception as e:
            _logger.error(f"Error accessing plugin manager for exports: {e}")


if __name__ == "__main__":
    pass
