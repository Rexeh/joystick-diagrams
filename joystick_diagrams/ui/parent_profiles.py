import logging

import qtawesome as qta
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractItemView, QListWidgetItem, QMainWindow

from joystick_diagrams.app_state import AppState
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.ui.qt_designer import parent_profile_management_ui

_logger = logging.getLogger(__name__)


class parent_profile_ui(QMainWindow, parent_profile_management_ui.Ui_Form):
    parentProfileChange = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()
        self.availableParentsComboBox.clear()
        self.listWidget.clear()
        self.addParentItem.clicked.connect(self.add_parent_profile)
        self.deleteParent.clicked.connect(self.remove_parent_profile)
        self.availableParentsComboBox.setMaxVisibleItems(15)
        self.currentActiveProfile: ProfileWrapper = None
        self.parentProfileChange.connect(self.save_profile_parent_maps)
        self.listWidget.clicked.connect(self.update_allowed_controls)

        # Updated terminology
        self.label.setText("Inherited Profiles")
        self.label_2.setText("Drag to reorder. Higher in list = higher priority.")
        self.addParentItem.setText("Add Inherited Profile")

        # Hide up/down buttons — replaced by drag-and-drop reordering
        self.parentUp.hide()
        self.parentDown.hide()

        # Enable drag-and-drop reordering on the list
        self.listWidget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.listWidget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.listWidget.model().rowsMoved.connect(self._on_rows_moved)

        self.deleteParent.setIcon(
            qta.icon("fa5s.trash-alt", color="white", color_disabled="white")
        )
        self.deleteParent.setProperty("class", "danger")

        self.availableParentsComboBox.setStyleSheet("color:white")
        self.availableParentsComboBox.setProperty("class", "view-binds-list")

        self.disable_parent_controls()

    def _on_rows_moved(self):
        """Handle drag-and-drop reordering."""
        self.parentProfileChange.emit()

    def disable_parent_controls(self):
        self.deleteParent.setDisabled(True)

    def update_allowed_controls(self, item: QModelIndex):
        self.deleteParent.setDisabled(False)

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
