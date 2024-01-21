import logging
import sys

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem
from qt_material import apply_stylesheet

from joystick_diagrams import app_init
from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui.mock_main import parent_profiles
from joystick_diagrams.ui.mock_main.qt_designer import configure_page_ui

_logger = logging.getLogger(__name__)


class configurePage(QMainWindow, configure_page_ui.Ui_Form):  # Refactor pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()
        self.treeWidget.header().setVisible(True)
        self.initialise_available_profiles()
        self.initialise_customise_binds()
        self.profileParentWidget = parent_profiles.parent_profile_ui()
        self.verticalLayout_6.addWidget(self.profileParentWidget)
        self.profileList.clicked.connect(self.handle_clicked_profile)
        self.profileToParentMapping = {}
        self.comboBox.activated.connect(self.load_binds_for_selected_profile)

    def get_profiles(self):
        return self.appState.profileObjectMapping

    def initialise_available_profiles(self):
        self.profileList.clear()
        profiles = self.get_profiles()
        for i in profiles.values():
            self.profileList.addItem(i.name)

    def initialise_customise_binds(self):
        profiles = self.appState.get_processed_profiles()
        self.treeWidget.clear()
        self.comboBox.clear()

        for key in profiles.keys():
            self.comboBox.addItem(key)

    def load_binds_for_selected_profile(self):
        selected_profile = self.comboBox.currentText()
        self.treeWidget.clear()

        profile_data = self.appState.get_processed_profile(selected_profile)

        for device_name, device_obj in profile_data.devices.items():
            device_item = QTreeWidgetItem(self.treeWidget)
            device_item.setText(0, device_name)  # Set device name in the first column
            self.treeWidget.addTopLevelItem(device_item)

            for input_obj in device_obj.inputs.values():
                input_item = QTreeWidgetItem(device_item)
                input_item.setText(0, "Input")
                input_item.setText(1, input_obj.identifier)
                input_item.setText(2, input_obj.command)

                for modifier_obj in input_obj.modifiers:
                    mod_item = QTreeWidgetItem(input_item)
                    mod_item.setText(0, "Modifier")
                    mod_item.setText(1, modifier_obj.command)
                    mod_item.setText(2, ", ".join(modifier_obj.modifiers))

    @Slot()
    def handle_clicked_profile(self, item):
        value = self.profileList.currentItem().text()
        self.profileParentWidget.set_profile_parent_map(value)


if __name__ == "__main__":
    logger = logging.basicConfig
    app = QApplication(sys.argv)
    app_init
    window = configurePage()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
