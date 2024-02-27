import logging

import qtawesome as qta
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QListWidgetItem, QMainWindow

from joystick_diagrams.app_state import AppState
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.ui.qt_designer import parent_profile_management_ui

_logger = logging.getLogger(__name__)


class parent_profile_ui(
    QMainWindow, parent_profile_management_ui.Ui_Form
):  # Refactor pylint: disable=too-many-instance-attributes
    parentProfileChange = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()
        self.availableParentsComboBox.clear()
        self.listWidget.clear()
        self.addParentItem.clicked.connect(self.add_parent_profile)
        self.parentUp.clicked.connect(self.change_parent_index_up)
        self.parentDown.clicked.connect(self.change_parent_index_down)
        self.deleteParent.clicked.connect(self.remove_parent_profile)
        self.currentActiveProfile: ProfileWrapper = None
        self.parentProfileChange.connect(self.save_profile_parent_maps)
        self.listWidget.clicked.connect(self.update_allowed_controls)

        self.parentUp.setIcon(
            qta.icon("fa5s.arrow-up", color="white", color_disabled="white")
        )
        self.parentUp.setText("UP       ")
        self.parentDown.setIcon(
            qta.icon("fa5s.arrow-down", color="white", color_disabled="white")
        )
        self.deleteParent.setIcon(
            qta.icon("fa5s.trash-alt", color="white", color_disabled="white")
        )
        self.deleteParent.setProperty("class", "danger")

        self.availableParentsComboBox.setStyleSheet("color:white")

        self.disable_parent_controls()

    def disable_parent_controls(self):
        self.deleteParent.setDisabled(True)
        self.parentDown.setDisabled(True)
        self.parentUp.setDisabled(True)

    def update_allowed_controls(self, item: QModelIndex):
        total_rows = self.listWidget.count() - 1
        item_index = item.row()

        self.deleteParent.setDisabled(False)

        if item_index > 0 and item_index < total_rows:
            self.deleteParent.setDisabled(False)
            self.parentDown.setDisabled(False)
            self.parentUp.setDisabled(False)

        if item_index == 0:
            self.parentUp.setDisabled(True)
            self.parentDown.setDisabled(False)

        if item_index == total_rows:
            self.parentUp.setDisabled(False)
            self.parentDown.setDisabled(True)

    def add_parent_profile(self):
        target_profile = self.availableParentsComboBox.currentData(
            Qt.ItemDataRole.UserRole
        )

        item = QListWidgetItem(
            QIcon(target_profile.profile_origin.icon),
            target_profile.profile_name,
        )
        item.setData(Qt.ItemDataRole.UserRole, target_profile)

        self.listWidget.addItem(item)
        self.availableParentsComboBox.removeItem(
            self.availableParentsComboBox.currentIndex()
        )
        self.parentProfileChange.emit()

    def remove_parent_profile(self):
        self.listWidget.takeItem(self.listWidget.currentRow())

        if self.listWidget.count() == 0:
            self.disable_parent_controls()
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

    def filter_available_parents(self):
        return [
            x
            for x in self.appState.profile_wrappers
            if x not in self.currentActiveProfile.parents
            and x != self.currentActiveProfile
        ]

    def save_profile_parent_maps(self):
        parent_profiles = [
            self.listWidget.item(x).data(Qt.ItemDataRole.UserRole)
            for x in range(self.listWidget.count())
        ]

        self.currentActiveProfile.update_parents_for_profile(parent_profiles)
        self.update_selectable_profiles()

    def load_profile_parent_maps(self, profile_wrapper: ProfileWrapper):
        self.listWidget.clear()

        _logger.debug(
            f"Loading profile parent maps for {profile_wrapper.profile_key}: Maps {profile_wrapper.parents}"
        )

        for parent in reversed(profile_wrapper.parents):
            item = QListWidgetItem(
                QIcon(parent.profile_origin.icon),
                parent.profile_name,
            )
            item.setData(Qt.ItemDataRole.UserRole, parent)

            self.listWidget.addItem(item)

    def update_selectable_profiles(self):
        self.availableParentsComboBox.clear()

        available_items = self.filter_available_parents()

        if not available_items:
            self.availableParentsComboBox.setPlaceholderText("No items available")
            self.addParentItem.setDisabled(True)
            return

        self.addParentItem.setDisabled(False)
        self.availableParentsComboBox.setPlaceholderText("")

        for item in available_items:
            self.availableParentsComboBox.addItem(
                QIcon(item.profile_origin.icon), item.profile_name, item
            )

    def set_profile_parent_map(self, profile_wrapper: ProfileWrapper):
        self.availableParentsComboBox.clear()
        self.listWidget.clear()

        self.currentActiveProfile = profile_wrapper

        # Get the existing mappings if exists
        self.load_profile_parent_maps(self.currentActiveProfile)

        self.update_selectable_profiles()


if __name__ == "__main__":
    pass
