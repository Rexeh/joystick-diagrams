import logging
import os
from pathlib import Path

import qtawesome as qta  # type: ignore
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTreeWidgetItem

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_device_management import (
    add_update_device_template_path,
)
from joystick_diagrams.export import export
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.ui.device_setup import DeviceSetup
from joystick_diagrams.ui.export_settings import ExportSettings
from joystick_diagrams.ui.qt_designer import export_ui
from joystick_diagrams.utils import install_root

_logger = logging.getLogger(__name__)


class ExportPage(
    QMainWindow, export_ui.Ui_Form
):  # Refactor pylint: disable=too-many-instance-attributes
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
        self.setTemplateButton.setStyleSheet(
            """
            QPushButton:disabled{background-color:grey}QPushButton{background-color:#2980b9;color:white;font-size:14px;border-radius:3px;border:none}
            """
        )
        self.setTemplateButton.setDisabled(True)

        self.ExportButton.setIcon(
            qta.icon("fa5s.file-export", color="white", color_disabled="white")
        )
        self.ExportButton.setStyleSheet(
            """
            QPushButton:disabled{background-color:grey}QPushButton{background-color:#27ae60;color:white;font-size:14px;border-radius:3px;border:none}
            """
        )
        self.ExportButton.setIconSize(QSize(35, 35))

        # Include Device setup Widget
        self.device_widget = DeviceSetup()
        self.device_widget.device_item_selected.connect(self.change_template_button)
        self.horizontalLayout.addWidget(self.device_widget)
        self.device_widget.number_of_selected_profiles.connect(
            self.update_export_button_state
        )

        ## Include Export Settings Panel
        self.export_settings_widget = ExportSettings()
        self.export_settings_container.addWidget(self.export_settings_widget)

        # Defaults
        self.update_export_button_state(0)  # Set the export button state

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
            caption="Select an SVG file to use as a template",
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
        _save = add_update_device_template_path(row_guid_data, template_path.__str__())

        if _save:
            self.device_widget.devices_updated.emit()

    def get_items_to_export(self) -> list[ExportDevice]:
        return self.device_widget.get_selected_export_items()

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

        # TODO rework exporter structure > Push into async
        # TODO use case where two devices have same NAME but different GUIDS > Leads to export overwriting another
        for item in items_to_export:
            export(item, self.export_settings_widget.export_location)

        QMessageBox.information(
            self,
            "Items exported",
            f"{len(items_to_export)} items were exported to {self.export_settings_widget.export_location}",
            buttons=QMessageBox.StandardButton.Ok,
            defaultButton=QMessageBox.StandardButton.Ok,
        )


if __name__ == "__main__":
    pass
