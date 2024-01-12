import logging
import sys

from PySide6.QtCore import QDir, QMetaMethod, QObject, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QListWidgetItem, QMainWindow
from qt_material import apply_stylesheet

from joystick_diagrams.app_state import appState
from joystick_diagrams.ui.mock_main.qt_designer import parent_profile_management_ui

_logger = logging.getLogger(__name__)


class parent_profile_ui(
    QMainWindow, parent_profile_management_ui.Ui_Form
):  # Refactor pylint: disable=too-many-instance-attributes
    parentProfileChange = Signal()
    parentProfileChange = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = appState()
        self.availableParentsComboBox.clear()
        self.listWidget.clear()
        self.addParentItem.clicked.connect(self.add_parent_profile)
        self.parentUp.clicked.connect(self.change_parent_index_up)
        self.parentDown.clicked.connect(self.change_parent_index_down)
        self.deleteParent.clicked.connect(self.remove_parent_profile)
        self.currentActiveProfile = None
        self.parentProfileChange.connect(self.save_profile_parent_maps)

    def add_parent_profile(self):
        target_profile = self.availableParentsComboBox.currentText()
        self.listWidget.addItem(target_profile)
        self.availableParentsComboBox.removeItem(self.availableParentsComboBox.currentIndex())
        self.parentProfileChange.emit()

    def remove_parent_profile(self):
        item = self.listWidget.takeItem(self.listWidget.currentRow())
        self.availableParentsComboBox.addItem(item.text())
        self.parentProfileChange.emit()

    def change_parent_index_up(self):
        current_row = self.listWidget.currentRow()
        current_item = self.listWidget.takeItem(current_row)
        self.listWidget.insertItem(current_row - 1, current_item)
        self.parentProfileChange.emit()

    def change_parent_index_down(self):
        current_row = self.listWidget.currentRow()
        current_item = self.listWidget.takeItem(current_row)
        self.listWidget.insertItem(current_row + 1, current_item)

        self.parentProfileChange.emit()

    def filter_available_parents(self, target_key: str, available_keys: list[str], used_keys: list[str]):
        return [x for x in available_keys if x not in used_keys and x != target_key]

    def save_profile_parent_maps(self):
        parent_profiles = [self.listWidget.item(x).text() for x in range(self.listWidget.count())]
        self.appState.profileParentMapping[self.get_current_active_profile()] = parent_profiles
        _logger.debug(f"Current profile parent mappings: {self.appState.profileParentMapping}")

    def load_profile_parent_maps(self, profile_identifier: str):
        mappings = self.appState.profileParentMapping.get(profile_identifier)

        if not mappings:
            return []
        return mappings

    def get_current_active_profile(self):
        return self.currentActiveProfile

    def get_available_profile_names(self):
        return self.appState.profileObjectMapping.keys()

    def set_profile_parent_map(self, profile_identifier: str):
        self.availableParentsComboBox.clear()
        self.listWidget.clear()

        self.currentActiveProfile = profile_identifier
        # Get the existing mappings if exists
        saved_profile_parent_map = self.load_profile_parent_maps(profile_identifier)

        if saved_profile_parent_map:
            self.listWidget.addItems(saved_profile_parent_map)

        # Populate combo box with available parents
        filered_items = self.filter_available_parents(
            profile_identifier, self.get_available_profile_names(), saved_profile_parent_map
        )
        self.availableParentsComboBox.addItems(filered_items)


if __name__ == "__main__":
    logger = logging.basicConfig
    app = QApplication(sys.argv)
    window = parent_profile_ui()
    window.show()
    apply_stylesheet(app, theme="dark_blue.xml", invert_secondary=False)
    app.exec()
