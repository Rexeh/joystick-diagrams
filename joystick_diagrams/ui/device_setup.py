import logging

import qtawesome as qta  # type:  ignore
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTreeWidgetItem,
)

from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.ui.device_setup_controller import (
    get_export_devices,
)
from joystick_diagrams.ui.qt_designer import device_setup_ui

_logger = logging.getLogger(__name__)


class DeviceSetup(QMainWindow, device_setup_ui.Ui_Form):
    devices_updated = Signal()
    device_item_selected = Signal(object)
    device_checkstate_changed = Signal()
    number_of_selected_profiles = Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setupUi(self)

        # Connections
        self.treeWidget.itemChanged.connect(self.handle_item_change)
        self.devices_updated.connect(self.initialise_ui)
        self.device_checkstate_changed.connect(self.update_number_of_checked_items)

        # UI Setup
        self.device_header = QTreeWidgetItem()
        self.device_header.setText(0, "Device")

        self.device_header.setText(1, "Profile")
        self.device_header.setSizeHint(1, QSize(100, 25))
        self.device_header.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
        self.device_header.setText(2, "Status")

        self.treeWidget.setHeaderItem(self.device_header)
        self.treeWidget.setIconSize(QSize(20, 20))

        self.treeWidget.setColumnCount(3)
        self.treeWidget.itemClicked.connect(self.device_item_clicked)
        self.treeWidget.header().setStretchLastSection(True)
        self.treeWidget.header().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.treeWidget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.treeWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # Icon Setup
        self.good_icon = qta.icon(
            "fa5s.check-circle",
            color="green",
        )

        self.warning_icon = qta.icon(
            "fa5s.exclamation-triangle",
            color="orange",
        )

        self.bad_icon = qta.icon(
            "fa5s.times-circle",
            color="red",
            color_active="red",
            opacity=0.7,
            scale_factor=1,
        )

        # Init
        self.initialise_ui()

    def initialise_ui(self):
        devices = get_export_devices()

        self.add_devices_to_widget(devices)

    def update_number_of_checked_items(self):
        """Checks the number of active items in tree, to emit to consumers"""

        _count = 0
        for top_level_id in range(self.treeWidget.topLevelItemCount()):
            top_level_item = self.treeWidget.topLevelItem(top_level_id)
            for child_item_id in range(top_level_item.childCount()):
                _state = top_level_item.child(child_item_id).checkState(0)
                if _state == Qt.CheckState.Checked:
                    _count = _count + 1

        self.number_of_selected_profiles.emit(_count)

    def get_all_root_nodes(self) -> list[QTreeWidgetItem]:
        roots: list[QTreeWidgetItem] = []
        for root_id in range(self.treeWidget.topLevelItemCount()):
            roots.append(self.treeWidget.topLevelItem(root_id))
        return roots

    def get_children_for_root_node(
        self, root: QTreeWidgetItem
    ) -> list[QTreeWidgetItem]:
        children: list[QTreeWidgetItem] = []
        for child_id in range(root.childCount()):
            children.append(root.child(child_id))
        return children

    def one_or_more_checkstate_checked(self, items: list[QTreeWidgetItem]) -> bool:
        "Returns True if any QTreeWidget items have a CHECKED state for COL0"
        for widget_item in items:
            if widget_item.checkState(0) == Qt.CheckState.Checked:
                return True
        return False

    def get_selected_export_items(self) -> list[ExportDevice]:
        roots = self.get_all_root_nodes()

        export_devices: list[ExportDevice] = []

        for root in roots:
            children = self.get_children_for_root_node(root)
            for child in children:
                if child.checkState(0) == Qt.CheckState.Checked:
                    export_devices.append(child.data(0, Qt.ItemDataRole.UserRole))

        return export_devices

    def set_checkstate(self, items: list[QTreeWidgetItem], state: Qt.CheckState):
        "Sets the checkstate for groups of QTreeWidgetItems"
        for widget_item in items:
            widget_item.setCheckState(0, state)

    def handle_item_change(self, item: QTreeWidgetItem):
        # Get Item Check State
        parent_node = item.parent()
        item_check_state = item.checkState(0)
        self.device_checkstate_changed.emit()

        # Scenario 1- Clicked a parent item
        if parent_node is None:
            _child_items = self.get_children_for_root_node(item)
            _check = self.one_or_more_checkstate_checked(_child_items)

            if item_check_state == Qt.CheckState.Unchecked:
                self.set_checkstate(_child_items, Qt.CheckState.Unchecked)

            if item_check_state == Qt.CheckState.Checked:
                if not _check:
                    self.set_checkstate(_child_items, Qt.CheckState.Checked)

        # Scenario 2 - Clicked a child item
        if parent_node:
            if item_check_state == Qt.CheckState.Checked:
                parent_node.setCheckState(0, Qt.CheckState.Checked)
            if item_check_state == Qt.CheckState.Unchecked:
                _child_items_states = self.one_or_more_checkstate_checked(
                    self.get_children_for_root_node(parent_node)
                )
                if _child_items_states is False:
                    parent_node.setCheckState(0, Qt.CheckState.Unchecked)

    def device_item_clicked(self, data):
        self.device_item_selected.emit(data)

    def view_device_errors(self):
        current_treewidget_row = self.treeWidget.currentItem()
        data = current_treewidget_row.data(0, Qt.ItemDataRole.UserRole)

        # Format the text, this is horrible

        message_content = f"""
            <h2>Your template {data.template_file_name} is missing {len(data.errors)} controls</h2>
            <strong></strong>
            <p>This won't prevent an export, but you will be missing binds on your final export</p>

            <div class="container" style="inline-size: 100px; overflow-wrap: break-word;">
                <p>
                {data.errors}
                </p>
            </div>

        """

        msgBox = QMessageBox()
        msgBox.setWindowTitle(f"{data.device_name}")
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setText(message_content)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.setDefaultButton(QMessageBox.Ok)
        msgBox.exec()

    def add_devices_to_widget(self, export_devices: list[ExportDevice]):
        tree_roots = []
        child_nodes = []
        self.treeWidget.clear()

        identifiers = set([(x.device_id, x.device_name) for x in export_devices])

        def return_top_level_icon_state(
            children_have_template_issues: bool, children_have_errors: bool
        ) -> tuple[QIcon, str]:
            if children_have_template_issues:
                return (self.bad_icon, "A template is not configured")

            if children_have_errors:
                return (self.warning_icon, "One or more profiles have problems")

            return (self.good_icon, "")

        for device_identifier, device_name in identifiers:
            root_item = QTreeWidgetItem()
            # root_item.setStatusTip(0, identifier)
            root_item.setToolTip(0, f"Device GUID: {device_identifier}")
            root_item.setData(0, Qt.ItemDataRole.UserRole, device_identifier)
            root_item.setText(0, device_name)

            # Get the child items for the root identifier
            child_items = [
                x for x in export_devices if x.device_id == device_identifier
            ]

            root_profile_text = (
                f"{len(child_items)} Profiles"
                if len(child_items) > 1
                else f"{len(child_items)} Profile"
            )

            root_item.setText(1, root_profile_text)
            root_item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            # Detect if any of the potential children have a missing template, if so all items will be missing template
            children_have_template_issues = bool(
                [x.has_template for x in child_items if not x.has_template]
            )

            # Detect if any of the children have errors, one or more may have errors - Which should trigger a warning
            children_have_errors = bool([x.errors for x in child_items if x.errors])

            root_icon_state, root_message = return_top_level_icon_state(
                children_have_template_issues, children_have_errors
            )

            # For items without templates missing, add their child profiles to tree
            if not children_have_template_issues:
                # Add export tree root option
                root_item.setCheckState(0, Qt.CheckState.Unchecked)

                for child in child_items:
                    child_item = QTreeWidgetItem()
                    child_item.setData(0, Qt.ItemDataRole.UserRole, child)
                    child_item.setText(1, child.profile_wrapper.profile_name)
                    child_item.setIcon(
                        1, QIcon(child.profile_wrapper.profile_origin.icon)
                    )

                    # Add export option for child
                    child_item.setCheckState(0, Qt.CheckState.Unchecked)

                    # Get the child icon state where template not exists / or errors bucket contains entries
                    child_icon_state, child_message = return_top_level_icon_state(
                        not child.has_template, bool(child.errors)
                    )

                    child_item.setIcon(2, child_icon_state)

                    child_nodes.append(child_item)

            root_item.addChildren(child_nodes)
            root_item.setIcon(
                2,
                root_icon_state,
            )
            if root_message:
                root_item.setText(2, root_message)

            tree_roots.append(root_item)

        self.treeWidget.addTopLevelItems(tree_roots)
        self.add_view_error_controls_to_tree()
        self.treeWidget.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def add_view_error_controls_to_tree(self):
        """Adds in widgets to existing treeWidget items. This has to be done post tree setup due to QT"""
        for i in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(i)
            for c in range(item.childCount()):
                child_item = item.child(c)
                child_data = child_item.data(0, Qt.ItemDataRole.UserRole)

                if child_data.errors:
                    button = QPushButton("View Errors")
                    button.setProperty("class", "warning")
                    button.setFixedWidth(150)
                    button.setFixedHeight(25)
                    button.setStyleSheet(
                        "padding-left: 5px; padding-right: 3px;"
                        "padding-top: 1px; padding-bottom: 1px;"
                    )
                    button.clicked.connect(self.view_device_errors)
                    self.treeWidget.setItemWidget(child_item, 2, button)


if __name__ == "__main__":
    pass
