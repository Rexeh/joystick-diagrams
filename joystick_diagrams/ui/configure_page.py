import logging

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QBrush, QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QSplitter,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.input.axis import Axis, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat
from joystick_diagrams.profile_wrapper import ProfileWrapper
from joystick_diagrams.ui import parent_profiles
from joystick_diagrams.ui.qt_designer import configure_page_ui
from joystick_diagrams.ui.widgets.section_header import SectionHeader

_logger = logging.getLogger(__name__)

CUSTOM_LABEL_COLOR = QColor("#34D399")
ORIGINAL_COMMAND_ROLE = Qt.ItemDataRole.UserRole

# Dot colors per control type
TYPE_DOT_COLORS = {
    Button: "#16a085",  # teal
    Axis: "#2980b9",  # blue
    Hat: "#5865F2",  # indigo
    AxisSlider: "#2980b9",  # blue (same as axis)
}
MOD_DOT_COLOR = "#E67E22"  # warm amber


class configurePage(QMainWindow, configure_page_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.appState = AppState()

        # Replace heading with SectionHeader
        self.heading_label.hide()
        self.section_header = SectionHeader(
            "fa5s.tools",
            "Customise & Review",
            "View binds, edit labels, and configure profile inheritance",
        )
        self.verticalLayout.insertWidget(0, self.section_header)

        # Hide the tab widget — we replace it with a splitter layout
        self.tabWidget.hide()

        # Build the new unified layout: left panel (profiles) | right panel (binds)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT PANEL: Profile list + parent management ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        profiles_label = QLabel("Profiles")
        profiles_label.setProperty("class", "surface-card-title")
        left_layout.addWidget(profiles_label)

        # Profile list with origin badges
        self.profileList = QListWidget()
        self.profileList.setProperty("class", "view-binds-tree")
        self.profileList.setDragEnabled(False)
        self.profileList.clicked.connect(self._on_profile_selected)
        self.profileList.currentRowChanged.connect(
            lambda: self._on_profile_selected(self.profileList.currentIndex())
        )
        left_layout.addWidget(self.profileList)

        # Profile inheritance section
        inheritance_label = QLabel("Inherited Profiles")
        inheritance_label.setProperty("class", "surface-card-title")
        left_layout.addWidget(inheritance_label)

        inheritance_help = QLabel(
            "Binds from inherited profiles merge into the selected profile. "
            "Higher in the list = higher priority."
        )
        inheritance_help.setObjectName("device_help_label")
        inheritance_help.setWordWrap(True)
        left_layout.addWidget(inheritance_help)

        self.profileParentWidget = parent_profiles.parent_profile_ui()
        left_layout.addWidget(self.profileParentWidget)

        self.splitter.addWidget(left_panel)

        # === RIGHT PANEL: Search + Binds tree ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        binds_label = QLabel("Binds")
        binds_label.setProperty("class", "surface-card-title")
        right_layout.addWidget(binds_label)

        # Search/filter field
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        search_icon = QLabel()
        search_icon.setPixmap(
            qta.icon("fa5s.search", color="#9AA0A6").pixmap(QSize(14, 14))
        )
        search_icon.setFixedSize(14, 14)
        search_icon.setStyleSheet("background: transparent;")
        search_row.addWidget(search_icon)

        self.binds_search = QLineEdit()
        self.binds_search.setPlaceholderText("Filter binds...")
        self.binds_search.setProperty("class", "binds-search")
        self.binds_search.setClearButtonEnabled(True)
        self.binds_search.textChanged.connect(self._filter_binds_tree)
        search_row.addWidget(self.binds_search)

        right_layout.addLayout(search_row)

        # Binds tree widget (reuse the one from the UI file)
        self.viewBindsTreeWidget.setParent(right_panel)
        right_layout.addWidget(self.viewBindsTreeWidget)

        self.splitter.addWidget(right_panel)

        # Set splitter proportions: 35% left, 65% right
        self.splitter.setStretchFactor(0, 35)
        self.splitter.setStretchFactor(1, 65)
        self.splitter.setHandleWidth(2)

        self.verticalLayout.addWidget(self.splitter)

        # Configure the binds tree widget
        self.viewBindsTreeWidget.header().setVisible(True)
        self.viewBindsTreeWidget.setProperty("class", "view-binds-tree")
        self.viewBindsTreeWidget.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        # 2-column layout: Control | Action
        # Device root rows span all columns via setFirstColumnSpanned
        # Colored dot icons on col 0 indicate control type
        self.device_header = QTreeWidgetItem()
        self.device_header.setText(0, "Control")
        self.device_header.setText(1, "Action")

        self.viewBindsTreeWidget.setHeaderItem(self.device_header)
        self.viewBindsTreeWidget.setIconSize(QSize(10, 10))
        self.viewBindsTreeWidget.setWordWrap(False)
        self.viewBindsTreeWidget.setColumnCount(2)

        # Col 0 (Control): interactive, stable width
        # Col 1 (Action): stretches to fill remaining space
        self.viewBindsTreeWidget.header().setStretchLastSection(True)
        self.viewBindsTreeWidget.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.viewBindsTreeWidget.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.viewBindsTreeWidget.header().resizeSection(0, 180)
        self.viewBindsTreeWidget.header().setMinimumSectionSize(100)

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
        self.viewBindsTreeWidget.itemChanged.connect(self._handle_item_changed)

        # Context menu
        self.viewBindsTreeWidget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.viewBindsTreeWidget.customContextMenuRequested.connect(
            self.show_context_menu
        )

        # Icons
        self.device_icon = qta.icon("fa5s.gamepad", color="#9AA0A6")

        self.initialise_available_profiles()
        self._load_first_profile()

    def get_profiles(self):
        return self.appState.profile_wrappers

    def initialise_available_profiles(self):
        self.profileList.clear()

        profiles = self.get_profiles()
        for profile in profiles:
            # Create a custom widget for each profile showing origin badge
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, profile)
            item.setSizeHint(QSize(0, 44))

            widget = self._create_profile_item_widget(profile)
            self.profileList.addItem(item)
            self.profileList.setItemWidget(item, widget)

    def _create_profile_item_widget(self, profile: ProfileWrapper) -> QWidget:
        """Create a custom widget for profile list items with origin badge."""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Plugin icon
        icon_label = QLabel()
        icon_label.setPixmap(QIcon(profile.profile_origin.icon).pixmap(QSize(22, 22)))
        icon_label.setFixedSize(22, 22)
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)

        # Profile name
        name_label = QLabel(profile.profile_name)
        name_label.setStyleSheet(
            "color: #E8EAED; font-weight: bold; font-size: 12px; background: transparent;"
        )
        layout.addWidget(name_label, stretch=1)

        # Origin badge
        origin_badge = QLabel(profile.profile_origin.name)
        origin_badge.setStyleSheet(
            "color: #9AA0A6; font-size: 10px; background: #2c2f38; "
            "border: 1px solid #3C4043; border-radius: 4px; padding: 2px 6px;"
        )
        layout.addWidget(origin_badge)

        return widget

    def _load_first_profile(self):
        """Load the first profile's binds on initial display."""
        if self.profileList.count() > 0:
            self.profileList.setCurrentRow(0)
            self._on_profile_selected(self.profileList.currentIndex())

    def _on_profile_selected(self, index):
        """Handle profile selection from the unified left panel."""
        item = self.profileList.currentItem()
        if not item:
            return

        profile: ProfileWrapper = item.data(Qt.ItemDataRole.UserRole)

        # Load binds for this profile
        self._load_binds_for_profile(profile)

        # Load parent profile management for this profile
        self.profileParentWidget.set_profile_parent_map(profile)

    def _dot_icon(self, color: str) -> QIcon:
        """Return a small colored circle icon."""
        return qta.icon("fa5s.circle", color=color)

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

    def _load_binds_for_profile(self, profile_wrapper: ProfileWrapper):
        """Load binds tree for the given profile wrapper."""
        self.binds_search.clear()

        self.viewBindsTreeWidget.blockSignals(True)
        self.viewBindsTreeWidget.clear()

        profile_data = profile_wrapper.profile

        for device_obj in profile_data.get_devices().values():
            if self.appState.device_service.is_hidden(device_obj.guid):
                continue

            device_root = QTreeWidgetItem(self.viewBindsTreeWidget)
            device_root.setText(0, device_obj.name)
            device_root.setIcon(0, self.device_icon)
            device_root.setToolTip(0, device_obj.guid)
            device_root.setFlags(device_root.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Device rows span all columns — full width for long device names
            device_root.setFirstColumnSpanned(True)

            device_inputs = device_obj.get_combined_inputs().values()

            if not device_inputs:
                device_root.setText(0, f"{device_obj.name}  —  No inputs")

            for input_obj in device_inputs:
                input_node = QTreeWidgetItem(device_root)

                # Col 0: Colored dot + control identifier
                dot_color = TYPE_DOT_COLORS.get(
                    type(input_obj.input_control), "#9AA0A6"
                )
                input_node.setIcon(0, self._dot_icon(dot_color))
                input_node.setText(0, input_obj.input_control.identifier)

                # Col 1: Action label
                original_command = input_obj.command
                resolved = self.appState.label_service.resolve(original_command)
                input_node.setData(1, ORIGINAL_COMMAND_ROLE, original_command)
                input_node.setText(1, resolved)
                input_node.setFlags(input_node.flags() | Qt.ItemFlag.ItemIsEditable)
                self._set_custom_label_indicator(input_node, original_command)

                for modifier_obj in input_obj.modifiers:
                    modifier_node = QTreeWidgetItem(input_node)

                    # Col 0: Amber dot + modifier keys
                    mod_text = " + ".join(sorted(modifier_obj.modifiers))
                    modifier_node.setIcon(0, self._dot_icon(MOD_DOT_COLOR))
                    modifier_node.setText(0, mod_text)

                    # Col 1: Modified action label
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

        self.viewBindsTreeWidget.blockSignals(False)

    def _filter_binds_tree(self, text: str):
        """Filter the binds tree by hiding non-matching items."""
        text = text.lower().strip()

        for i in range(self.viewBindsTreeWidget.topLevelItemCount()):
            device = self.viewBindsTreeWidget.topLevelItem(i)
            any_child_visible = False

            for j in range(device.childCount()):
                child = device.child(j)
                control_text = child.text(0).lower()
                action_text = child.text(1).lower()

                match = not text or text in control_text or text in action_text

                # Also check modifier children
                if not match:
                    for k in range(child.childCount()):
                        mod = child.child(k)
                        if text in mod.text(0).lower() or text in mod.text(1).lower():
                            match = True
                            break

                child.setHidden(not match)
                if match:
                    any_child_visible = True

            device.setHidden(not any_child_visible and bool(text))

    @Slot(QTreeWidgetItem, int)
    def _handle_item_changed(self, item: QTreeWidgetItem, column: int):
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


if __name__ == "__main__":
    pass
