import logging

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QBrush, QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.input.axis import Axis, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.ui import parent_profiles
from joystick_diagrams.ui.qt_designer import configure_page_ui

_logger = logging.getLogger(__name__)

CUSTOM_LABEL_COLOR = QColor("#34D399")
ORIGINAL_COMMAND_ROLE = Qt.ItemDataRole.UserRole


class configurePage(QMainWindow, configure_page_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()
        self.viewBindsTreeWidget.header().setVisible(True)
        self.viewBindsTreeWidget.header().setStretchLastSection(True)
        self.viewBindsTreeWidget.header().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        self.viewBindsTreeWidget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.viewBindsTreeWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.viewBindsTreeWidget.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self.profileParentWidget = parent_profiles.parent_profile_ui()
        self.verticalLayout_6.addWidget(self.profileParentWidget)
        self.profileList.clicked.connect(self.handle_clicked_profile)
        self.profileList.setDragEnabled(False)

        self.viewBindsProfileList.currentIndexChanged.connect(
            self.load_binds_for_selected_profile
        )

        self.tabWidget.setProperty("class", "configure-tabwidget")
        self.viewBindsTreeWidget.setProperty("class", "view-binds-tree")
        self.viewBindsProfileList.setProperty("class", "view-binds-list")

        self.viewBindsProfileList.setIconSize(QSize(25, 25))

        # UI Setup
        self.device_header = QTreeWidgetItem()
        self.device_header.setText(0, "Device/Control")
        self.device_header.setSizeHint(0, QSize(150, 25))

        self.device_header.setText(1, "Action")
        self.device_header.setSizeHint(1, QSize(150, 25))

        self.viewBindsTreeWidget.setHeaderItem(self.device_header)
        self.viewBindsTreeWidget.setIconSize(QSize(20, 20))
        self.viewBindsTreeWidget.setWordWrap(False)
        self.viewBindsTreeWidget.setColumnCount(2)
        self.viewBindsTreeWidget.header().setMinimumSectionSize(200)
        self.viewBindsTreeWidget.header().setStretchLastSection(True)
        self.viewBindsTreeWidget.header().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.viewBindsTreeWidget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.viewBindsTreeWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # Enable inline editing via double-click on Action column
        self.viewBindsTreeWidget.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
        )
        self.viewBindsTreeWidget.itemChanged.connect(self.on_item_changed)

        # Context menu
        self.viewBindsTreeWidget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.viewBindsTreeWidget.customContextMenuRequested.connect(
            self.show_context_menu
        )

        # Icons
        self.device_icon = qta.icon(
            "fa5s.gamepad",
            color="#9AA0A6",
        )

        self.initialise_available_profiles()
        self.initialise_customise_binds()

    def get_profiles(self):
        return self.appState.profile_wrappers

    def initialise_available_profiles(self):
        self.profileList.clear()
        profiles = self.get_profiles()
        for profile in profiles:
            item = QListWidgetItem(
                QIcon(profile.profile_origin.icon), profile.profile_name
            )
            item.setData(Qt.ItemDataRole.UserRole, profile)
            self.profileList.addItem(item)

    def initialise_customise_binds(self):
        profile_wrappers = self.appState.profile_wrappers
        self.viewBindsTreeWidget.clear()
        self.viewBindsProfileList.clear()

        for profile in profile_wrappers:
            self.viewBindsProfileList.addItem(
                QIcon(profile.profile_origin.icon),
                profile.profile_name,
                profile,
            )

        self.viewBindsProfileList.setCurrentIndex(0)

    def create_control_type_widget(self, control: Axis | Button | Hat | AxisSlider):
        if isinstance(control, Axis):
            ctrl = QLabel("Axis")
            ctrl.setProperty("class", "device-control-pill axis")
            return ctrl

        if isinstance(control, Button):
            ctrl = QLabel("Button")
            ctrl.setProperty("class", "device-control-pill button")
            return ctrl

        if isinstance(control, Hat):
            ctrl = QLabel("Hat")
            ctrl.setProperty("class", "device-control-pill hat")
            return ctrl

        if isinstance(control, AxisSlider):
            ctrl = QLabel("Slider")
            ctrl.setProperty("class", "device-control-pill  axis")
            return ctrl

        ctrl = QLabel("UNKNOWN")
        ctrl.setProperty("class", "device-control-pill")
        return ctrl

    def _set_custom_label_indicator(self, item: QTreeWidgetItem, original: str):
        if self.appState.label_service.has_custom_label(original):
            item.setForeground(1, QBrush(CUSTOM_LABEL_COLOR))
        else:
            item.setForeground(1, QBrush(QColor("#E8EAED")))

    def _update_all_matching_items(self, original: str):
        """Walk the entire tree and update all items that share the same original command."""
        resolved = self.appState.label_service.resolve(original)
        iterator = QTreeWidgetItemIterator(self.viewBindsTreeWidget)
        while iterator.value():
            node = iterator.value()
            if node.data(1, ORIGINAL_COMMAND_ROLE) == original:
                node.setText(1, resolved)
                self._set_custom_label_indicator(node, original)
            iterator += 1

    def load_binds_for_selected_profile(self, index):
        if index == -1:
            # If box has been emptied due to profile load
            return

        selected_profile: ProfileWrapper = self.viewBindsProfileList.currentData()

        self.viewBindsTreeWidget.blockSignals(True)
        self.viewBindsTreeWidget.clear()

        profile_data = selected_profile.profile

        for device_obj in profile_data.get_devices().values():
            if self.appState.device_service.is_hidden(device_obj.guid):
                continue

            device_root = QTreeWidgetItem(self.viewBindsTreeWidget)

            device_root.setText(0, device_obj.name)
            device_root.setIcon(0, self.device_icon)
            device_root.setToolTip(0, device_obj.guid)
            # Device root should not be editable
            device_root.setFlags(device_root.flags() & ~Qt.ItemFlag.ItemIsEditable)

            device_inputs = device_obj.get_combined_inputs().values()

            if not device_inputs:
                device_root.setText(1, "No inputs for device")

            for input_obj in device_inputs:
                input_node = QTreeWidgetItem(device_root)

                # Store original command and display resolved label
                original_command = input_obj.command
                resolved = self.appState.label_service.resolve(original_command)
                input_node.setData(1, ORIGINAL_COMMAND_ROLE, original_command)
                input_node.setText(1, resolved)
                input_node.setFlags(input_node.flags() | Qt.ItemFlag.ItemIsEditable)
                self._set_custom_label_indicator(input_node, original_command)

                device_root.addChild(input_node)

                control_widget = self.create_control_type_widget(
                    input_obj.input_control
                )
                control_widget.setText(input_obj.input_control.identifier)

                self.viewBindsTreeWidget.setItemWidget(input_node, 0, control_widget)

                for modifier_obj in input_obj.modifiers:
                    modifier_node = QTreeWidgetItem(input_node)

                    modifier_node.setText(0, str(modifier_obj.modifiers))

                    # Store original modifier command and display resolved label
                    original_mod_command = modifier_obj.command
                    resolved_mod = self.appState.label_service.resolve(
                        original_mod_command
                    )
                    modifier_node.setData(
                        1, ORIGINAL_COMMAND_ROLE, original_mod_command
                    )
                    modifier_node.setText(1, resolved_mod)
                    modifier_node.setFlags(
                        modifier_node.flags() | Qt.ItemFlag.ItemIsEditable
                    )
                    self._set_custom_label_indicator(
                        modifier_node, original_mod_command
                    )

            self.viewBindsTreeWidget.addTopLevelItem(device_root)

        self.viewBindsTreeWidget.blockSignals(False)

    @Slot(QTreeWidgetItem, int)
    def on_item_changed(self, item: QTreeWidgetItem, column: int):
        if column != 1:
            return

        original = item.data(1, ORIGINAL_COMMAND_ROLE)
        if original is None:
            return

        new_text = item.text(1).strip()

        self.viewBindsTreeWidget.blockSignals(True)

        if not new_text or new_text == original:
            self.appState.label_service.remove_label(original)
        else:
            self.appState.label_service.set_label(original, new_text)

        self._update_all_matching_items(original)
        self.viewBindsTreeWidget.blockSignals(False)

    @Slot()
    def show_context_menu(self, position):
        item = self.viewBindsTreeWidget.itemAt(position)
        if not item:
            return

        original = item.data(1, ORIGINAL_COMMAND_ROLE)

        # Device root node (no original command data) — offer Hide Device
        if original is None and item.parent() is None:
            guid = item.toolTip(0)
            name = item.text(0)
            if not guid:
                return
            menu = QMenu(self)
            hide_action = menu.addAction("Hide Device")
            action = menu.exec(
                self.viewBindsTreeWidget.viewport().mapToGlobal(position)
            )
            if action == hide_action:
                self.appState.device_service.set_hidden(guid, name, True)
                index = self.viewBindsTreeWidget.indexOfTopLevelItem(item)
                if index >= 0:
                    self.viewBindsTreeWidget.takeTopLevelItem(index)
            return

        if original is None:
            return

        menu = QMenu(self)

        edit_action = menu.addAction("Edit Label")
        reset_action = menu.addAction("Reset to Original")

        has_custom = self.appState.label_service.has_custom_label(original)
        reset_action.setEnabled(has_custom)

        action = menu.exec(self.viewBindsTreeWidget.viewport().mapToGlobal(position))

        if action == edit_action:
            self.viewBindsTreeWidget.editItem(item, 1)
        elif action == reset_action:
            self.viewBindsTreeWidget.blockSignals(True)
            self.appState.label_service.remove_label(original)
            self._update_all_matching_items(original)
            self.viewBindsTreeWidget.blockSignals(False)

    @Slot()
    def handle_clicked_profile(self, item):
        value = self.profileList.currentItem().data(Qt.ItemDataRole.UserRole)
        self.profileParentWidget.set_profile_parent_map(value)


if __name__ == "__main__":
    pass
