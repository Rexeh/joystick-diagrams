import logging

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QTreeWidgetItem,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.input.axis import Axis, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.ui import parent_profiles
from joystick_diagrams.ui.qt_designer import configure_page_ui

_logger = logging.getLogger(__name__)


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

        # Icons
        self.device_icon = qta.icon(
            "fa5s.gamepad",
            color="#120303",
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
        ctrl.setStyleSheet("background:orange;max-width:30px")
        return ctrl

    def load_binds_for_selected_profile(self, index):
        if index == -1:
            # If box has been emptied due to profile load
            return

        selected_profile: ProfileWrapper = self.viewBindsProfileList.currentData()

        self.viewBindsTreeWidget.clear()

        profile_data = selected_profile.profile

        for device_obj in profile_data.get_devices().values():
            device_root = QTreeWidgetItem(self.viewBindsTreeWidget)

            device_root.setText(0, device_obj.name)
            device_root.setIcon(0, self.device_icon)
            device_root.setToolTip(0, device_obj.guid)

            device_inputs = device_obj.get_combined_inputs().values()

            if not device_inputs:
                device_root.setText(1, "No inputs for device")

            for input_obj in device_inputs:
                input_node = QTreeWidgetItem(device_root)

                # input_node.setText(0, input_obj.input_control.identifier)
                input_node.setText(1, input_obj.command)

                device_root.addChild(input_node)

                control_widget = self.create_control_type_widget(
                    input_obj.input_control
                )
                control_widget.setText(input_obj.input_control.identifier)

                self.viewBindsTreeWidget.setItemWidget(input_node, 0, control_widget)

                for modifier_obj in input_obj.modifiers:
                    modifier_node = QTreeWidgetItem(input_node)

                    modifier_node.setText(0, str(modifier_obj.modifiers))
                    modifier_node.setText(1, modifier_obj.command)

            self.viewBindsTreeWidget.addTopLevelItem(device_root)

    @Slot()
    def handle_clicked_profile(self, item):
        value = self.profileList.currentItem().data(Qt.ItemDataRole.UserRole)
        self.profileParentWidget.set_profile_parent_map(value)


if __name__ == "__main__":
    pass
