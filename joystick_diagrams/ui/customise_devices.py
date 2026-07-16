import logging
import os
from collections import defaultdict
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db.db_device_management import (
    add_update_device_template_path,
    get_device_template_path,
    remove_template_path_from_device,
)
from joystick_diagrams.utils import install_root

_logger = logging.getLogger(__name__)


class CustomiseDevices(QWidget):
    devices_changed = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.appState = AppState()
        self._selected_guid: str | None = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # Help text
        help_text = QLabel(
            "Manage all detected devices below. Select a device to view its details, "
            "set up aliases, assign templates, or toggle visibility."
        )
        help_text.setObjectName("device_help_label")
        help_text.setWordWrap(True)
        root_layout.addWidget(help_text)

        # Master-detail splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT PANEL: Device list ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        devices_header_row = QHBoxLayout()
        devices_header_row.setSpacing(8)

        devices_label = QLabel("Devices")
        devices_label.setProperty("class", "surface-card-title")
        devices_header_row.addWidget(devices_label, stretch=1)

        self._show_hidden_cb = QCheckBox("Show hidden")
        self._show_hidden_cb.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        self._show_hidden_cb.setChecked(False)
        self._show_hidden_cb.stateChanged.connect(self.refresh)
        devices_header_row.addWidget(self._show_hidden_cb)

        left_layout.addLayout(devices_header_row)

        self.device_list = QListWidget()
        self.device_list.setProperty("class", "view-binds-tree")
        self.device_list.currentRowChanged.connect(self._on_device_selected)
        left_layout.addWidget(self.device_list)

        self.splitter.addWidget(left_panel)

        # === RIGHT PANEL: Detail panel ===
        self._detail_panel = QWidget()
        self._detail_layout = QVBoxLayout(self._detail_panel)
        self._detail_layout.setContentsMargins(8, 0, 0, 0)
        self._detail_layout.setSpacing(16)

        # Empty state placeholder
        self._empty_state = QLabel("Select a device to view its details")
        self._empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_state.setStyleSheet(
            "color: #9AA0A6; font-style: italic; padding: 40px;"
        )
        self._detail_layout.addWidget(self._empty_state)

        # Detail content container (hidden until a device is selected)
        self._detail_content = QWidget()
        detail_content_layout = QVBoxLayout(self._detail_content)
        detail_content_layout.setContentsMargins(0, 0, 0, 0)
        detail_content_layout.setSpacing(16)

        # -- Header: device name + visibility toggle --
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self._device_name_label = QLabel()
        self._device_name_label.setStyleSheet(
            "color: #E8EAED; font-weight: bold; font-size: 16px;"
        )
        header_row.addWidget(self._device_name_label, stretch=1)

        self._visible_cb = QCheckBox("Visible")
        self._visible_cb.stateChanged.connect(self._on_visibility_changed)
        header_row.addWidget(self._visible_cb)

        detail_content_layout.addLayout(header_row)

        # -- GUID section --
        guid_row = QHBoxLayout()
        guid_row.setSpacing(8)

        self._guid_label = QLabel()
        self._guid_label.setStyleSheet(
            "color: #9AA0A6; font-family: monospace; font-size: 12px;"
        )
        self._guid_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        guid_row.addWidget(self._guid_label, stretch=1)

        copy_btn = QPushButton()
        copy_btn.setIcon(qta.icon("fa5s.copy", color="#9AA0A6"))
        copy_btn.setIconSize(QSize(14, 14))
        copy_btn.setFixedSize(QSize(30, 30))
        copy_btn.setToolTip("Copy GUID to clipboard")
        copy_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(76, 139, 245, 0.15); border-radius: 4px; }"
        )
        copy_btn.clicked.connect(self._copy_guid)
        guid_row.addWidget(copy_btn)

        detail_content_layout.addLayout(guid_row)

        # -- Display Name section --
        display_name_label = QLabel("Display Name")
        display_name_label.setStyleSheet("font-weight: bold; color: #E8EAED;")
        detail_content_layout.addWidget(display_name_label)

        self._original_name_label = QLabel()
        self._original_name_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        detail_content_layout.addWidget(self._original_name_label)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        self._custom_name_input = QLineEdit()
        self._custom_name_input.setPlaceholderText("Enter a custom name...")
        self._custom_name_input.setStyleSheet(
            "QLineEdit {"
            "  color: #E8EAED;"
            "  background-color: #252830;"
            "  border: 1px solid #3C4043;"
            "  border-radius: 4px;"
            "  padding: 8px 12px;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #4C8BF5;"
            "}"
            "QLineEdit::placeholder {"
            "  color: #6B7280;"
            "}"
        )
        self._custom_name_input.editingFinished.connect(self._on_custom_name_changed)
        name_row.addWidget(self._custom_name_input, stretch=1)

        self._reset_name_btn = QPushButton()
        self._reset_name_btn.setIcon(qta.icon("fa5s.undo", color="#9AA0A6"))
        self._reset_name_btn.setIconSize(QSize(14, 14))
        self._reset_name_btn.setFixedSize(QSize(30, 30))
        self._reset_name_btn.setToolTip("Reset to original name")
        self._reset_name_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.15); border-radius: 4px; }"
        )
        self._reset_name_btn.clicked.connect(self._on_reset_name)
        name_row.addWidget(self._reset_name_btn)

        detail_content_layout.addLayout(name_row)

        # -- Profiles section --
        profiles_section_label = QLabel("Profiles")
        profiles_section_label.setStyleSheet("font-weight: bold; color: #E8EAED;")
        detail_content_layout.addWidget(profiles_section_label)

        self._profiles_container = QWidget()
        self._profiles_layout = QVBoxLayout(self._profiles_container)
        self._profiles_layout.setContentsMargins(0, 0, 0, 0)
        self._profiles_layout.setSpacing(4)
        detail_content_layout.addWidget(self._profiles_container)

        # -- Alias section --
        alias_section_label = QLabel("Alias Target")
        alias_section_label.setStyleSheet("font-weight: bold; color: #E8EAED;")
        detail_content_layout.addWidget(alias_section_label)

        self._alias_combo = QComboBox()
        self._alias_combo.setMaxVisibleItems(15)
        self._alias_combo.currentIndexChanged.connect(self._on_alias_changed)
        detail_content_layout.addWidget(self._alias_combo)

        alias_help = QLabel("Makes this device appear as the target, merging bindings.")
        alias_help.setStyleSheet("color: #9AA0A6; font-style: italic; font-size: 11px;")
        alias_help.setWordWrap(True)
        detail_content_layout.addWidget(alias_help)

        # -- Template section --
        template_section_label = QLabel("Template")
        template_section_label.setStyleSheet("font-weight: bold; color: #E8EAED;")
        detail_content_layout.addWidget(template_section_label)

        self._template_label = QLabel()
        self._template_label.setStyleSheet("color: #E8EAED; font-size: 12px;")
        detail_content_layout.addWidget(self._template_label)

        template_btn_row = QHBoxLayout()
        template_btn_row.setSpacing(8)

        self._change_template_btn = QPushButton("Change...")
        self._change_template_btn.setIcon(qta.icon("fa5s.folder-open", color="white"))
        self._change_template_btn.setIconSize(QSize(14, 14))
        self._change_template_btn.setProperty("class", "plugin-setup-button")
        self._change_template_btn.clicked.connect(self._on_template_change)
        template_btn_row.addWidget(self._change_template_btn)

        self._clear_template_btn = QPushButton("Clear")
        self._clear_template_btn.setIcon(qta.icon("fa5s.times", color="#EF4444"))
        self._clear_template_btn.setIconSize(QSize(14, 14))
        self._clear_template_btn.setProperty("class", "plugin-setup-button")
        self._clear_template_btn.clicked.connect(self._on_template_clear)
        template_btn_row.addWidget(self._clear_template_btn)

        template_btn_row.addStretch()
        detail_content_layout.addLayout(template_btn_row)

        detail_content_layout.addStretch()

        self._detail_content.hide()
        self._detail_layout.addWidget(self._detail_content)

        self.splitter.addWidget(self._detail_panel)

        # Splitter proportions: 35% list, 65% detail
        self.splitter.setStretchFactor(0, 35)
        self.splitter.setStretchFactor(1, 65)
        self.splitter.setHandleWidth(2)

        root_layout.addWidget(self.splitter, stretch=1)

    # ── Data helpers ──

    def _get_all_known_devices(self) -> list[tuple[str, str]]:
        """Return sorted list of (guid, display_name) using custom names where set."""
        devices: dict[str, str] = {}
        for wrapper in self.appState.profile_wrappers:
            for guid, device in wrapper.original_profile.devices.items():
                if guid not in devices:
                    devices[guid] = self.appState.device_service.resolve_name(
                        guid, device.name
                    )
        return sorted(devices.items(), key=lambda x: x[1])

    def _get_original_device_name(self, guid: str) -> str:
        """Return the original (unmodified) device name from profile data."""
        for wrapper in self.appState.profile_wrappers:
            if guid in wrapper.original_profile.devices:
                return wrapper.original_profile.devices[guid].name
        return guid

    def _get_device_profile_usage(self, guid: str) -> dict[str, tuple[int, str]]:
        """Return {plugin_name: (profile_count, icon_path)} for a device GUID."""
        usage: dict[str, list] = defaultdict(list)
        icons: dict[str, str] = {}
        for wrapper in self.appState.profile_wrappers:
            if guid in wrapper.original_profile.devices:
                plugin_name = wrapper.profile_origin.name
                icons[plugin_name] = wrapper.profile_origin.icon
                usage[plugin_name].append(wrapper.profile_name)
        return {name: (len(profiles), icons[name]) for name, profiles in usage.items()}

    # ── Refresh ──

    def refresh(self):
        """Rebuild the device list from current app state."""
        # Remember selection
        prev_guid = self._selected_guid
        show_hidden = self._show_hidden_cb.isChecked()

        self.device_list.clear()
        all_devices = self._get_all_known_devices()
        aliases = self.appState.device_alias_service.get_all_aliases()

        # Filter hidden devices unless checkbox is checked
        if not show_hidden:
            all_devices = [
                (guid, name)
                for guid, name in all_devices
                if not self.appState.device_service.is_hidden(guid)
            ]

        # Detect duplicate names to show GUID suffixes
        name_counts: dict[str, int] = defaultdict(int)
        for _, name in all_devices:
            name_counts[name] += 1

        restore_row = -1
        for idx, (guid, name) in enumerate(all_devices):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, guid)
            item.setSizeHint(QSize(0, 52))

            widget = self._create_device_list_item(
                guid, name, aliases, name_counts[name] > 1
            )
            self.device_list.addItem(item)
            self.device_list.setItemWidget(item, widget)

            if guid == prev_guid:
                restore_row = idx

        # Restore selection or show empty state
        if restore_row >= 0:
            self.device_list.setCurrentRow(restore_row)
            # Force detail refresh even if row index didn't change
            self._on_device_selected(restore_row)
        elif self.device_list.count() > 0:
            self.device_list.setCurrentRow(0)
        else:
            self._show_empty_state()

    def _create_device_list_item(
        self,
        guid: str,
        name: str,
        aliases: dict[str, str],
        show_guid_suffix: bool,
    ) -> QWidget:
        """Create a custom widget for a device list item."""
        has_template = get_device_template_path(guid) is not None
        is_aliased = guid in aliases
        is_hidden = self.appState.device_service.is_hidden(guid)

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Left side: name + GUID prefix
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel(name)
        name_style = "font-weight: bold; font-size: 12px; background: transparent;"
        if is_hidden:
            name_style += " color: #6B7280;"
        else:
            name_style += " color: #E8EAED;"
        name_label.setStyleSheet(name_style)
        text_col.addWidget(name_label)

        guid_prefix = guid[:8] if len(guid) >= 8 else guid
        guid_label = QLabel(guid_prefix)
        guid_label.setStyleSheet(
            "color: #6B7280; font-family: monospace; font-size: 10px; background: transparent;"
        )
        text_col.addWidget(guid_label)

        layout.addLayout(text_col, stretch=1)

        # Right side: status dots
        dots_col = QVBoxLayout()
        dots_col.setSpacing(2)
        dots_col.setContentsMargins(0, 0, 0, 0)
        dots_col.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        dot_size = QSize(8, 8)

        if has_template:
            dot = QLabel()
            dot.setPixmap(qta.icon("fa5s.circle", color="#34D399").pixmap(dot_size))
            dot.setFixedSize(dot_size)
            dot.setToolTip("Template assigned")
            dot.setStyleSheet("background: transparent;")
            dots_col.addWidget(dot)

        if is_aliased:
            dot = QLabel()
            dot.setPixmap(qta.icon("fa5s.circle", color="#4C8BF5").pixmap(dot_size))
            dot.setFixedSize(dot_size)
            dot.setToolTip("Aliased to another device")
            dot.setStyleSheet("background: transparent;")
            dots_col.addWidget(dot)

        if is_hidden:
            dot = QLabel()
            dot.setPixmap(qta.icon("fa5s.circle", color="#6B7280").pixmap(dot_size))
            dot.setFixedSize(dot_size)
            dot.setToolTip("Hidden")
            dot.setStyleSheet("background: transparent;")
            dots_col.addWidget(dot)

        layout.addLayout(dots_col)

        return widget

    # ── Detail panel ──

    def _show_empty_state(self):
        self._selected_guid = None
        self._detail_content.hide()
        self._empty_state.show()

    def _on_device_selected(self, row: int):
        if row < 0:
            self._show_empty_state()
            return

        item = self.device_list.item(row)
        if not item:
            self._show_empty_state()
            return

        guid = item.data(Qt.ItemDataRole.UserRole)
        self._selected_guid = guid
        self._populate_detail(guid)

    def _populate_detail(self, guid: str):
        """Populate the detail panel for the selected device."""
        self._empty_state.hide()
        self._detail_content.show()

        all_devices = self._get_all_known_devices()
        original_name = self._get_original_device_name(guid)
        display_name = self.appState.device_service.resolve_name(guid, original_name)

        # Header — show resolved display name
        self._device_name_label.setText(display_name)

        # GUID
        self._guid_label.setText(guid)

        # Display Name
        custom_name = self.appState.device_service.get_custom_name(guid)
        self._original_name_label.setText(f"Original: {original_name}")
        self._custom_name_input.blockSignals(True)
        self._custom_name_input.setText(custom_name or "")
        self._custom_name_input.blockSignals(False)
        self._reset_name_btn.setEnabled(custom_name is not None)

        # Visibility
        is_hidden = self.appState.device_service.is_hidden(guid)
        self._visible_cb.blockSignals(True)
        self._visible_cb.setChecked(not is_hidden)
        self._visible_cb.blockSignals(False)

        # Profile usage
        self._populate_profile_usage(guid)

        # Alias combo
        self._populate_alias_combo(guid, all_devices)

        # Template
        self._populate_template(guid)

    def _populate_profile_usage(self, guid: str):
        """Show which plugins/profiles use this device."""
        # Clear previous
        while self._profiles_layout.count():
            item = self._profiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        usage = self._get_device_profile_usage(guid)

        if not usage:
            no_usage = QLabel("No profiles use this device")
            no_usage.setStyleSheet(
                "color: #6B7280; font-style: italic; font-size: 11px;"
            )
            self._profiles_layout.addWidget(no_usage)
            return

        for plugin_name, (count, icon_path) in sorted(usage.items()):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 0, 0, 0)

            icon_label = QLabel()
            icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(16, 16)))
            icon_label.setFixedSize(16, 16)
            icon_label.setStyleSheet("background: transparent;")
            row.addWidget(icon_label)

            text = f"{plugin_name}: {count} profile{'s' if count != 1 else ''}"
            text_label = QLabel(text)
            text_label.setStyleSheet("color: #BDC1C6; font-size: 12px;")
            row.addWidget(text_label, stretch=1)

            container = QWidget()
            container.setLayout(row)
            self._profiles_layout.addWidget(container)

    def _populate_alias_combo(self, guid: str, all_devices: list[tuple[str, str]]):
        """Populate the alias target combo for the selected device."""
        self._alias_combo.blockSignals(True)
        self._alias_combo.clear()

        self._alias_combo.addItem("\u2014 None \u2014", None)

        # Detect duplicate names for disambiguation
        name_counts: dict[str, int] = defaultdict(int)
        for _, name in all_devices:
            name_counts[name] += 1

        for other_guid, other_name in all_devices:
            if other_guid == guid:
                continue
            label = other_name
            if name_counts[other_name] > 1:
                prefix = other_guid[:8] if len(other_guid) >= 8 else other_guid
                label = f"{other_name}  [{prefix}]"
            self._alias_combo.addItem(label, other_guid)

        # Set current alias if any
        current_target = self.appState.device_alias_service.get_all_aliases().get(guid)
        if current_target:
            idx = self._alias_combo.findData(current_target)
            if idx >= 0:
                self._alias_combo.setCurrentIndex(idx)

        self._alias_combo.blockSignals(False)

    def _populate_template(self, guid: str):
        """Show current template info."""
        template_path = get_device_template_path(guid)
        if template_path:
            self._template_label.setText(Path(template_path).name)
            self._template_label.setToolTip(template_path)
            self._template_label.setStyleSheet("color: #E8EAED; font-size: 12px;")
            self._clear_template_btn.setEnabled(True)
        else:
            self._template_label.setText("Not assigned")
            self._template_label.setToolTip("")
            self._template_label.setStyleSheet(
                "color: #6B7280; font-style: italic; font-size: 12px;"
            )
            self._clear_template_btn.setEnabled(False)

    # ── Actions ──

    def _copy_guid(self):
        if self._selected_guid:
            QApplication.clipboard().setText(self._selected_guid)

    def _on_custom_name_changed(self):
        if not self._selected_guid:
            return
        text = self._custom_name_input.text().strip()
        self.appState.device_service.set_custom_name(
            self._selected_guid, text if text else None
        )
        self.devices_changed.emit()
        self.refresh()

    def _on_reset_name(self):
        if not self._selected_guid:
            return
        self.appState.device_service.set_custom_name(self._selected_guid, None)
        self._custom_name_input.clear()
        self.devices_changed.emit()
        self.refresh()

    def _on_alias_changed(self, _index: int):
        if not self._selected_guid:
            return

        target_guid = self._alias_combo.currentData(Qt.ItemDataRole.UserRole)

        if target_guid is None:
            self.appState.device_alias_service.remove_alias(self._selected_guid)
        else:
            try:
                self.appState.device_alias_service.set_alias(
                    self._selected_guid, target_guid
                )
            except ValueError as e:
                QMessageBox.warning(self, "Alias Error", str(e))
                self._alias_combo.blockSignals(True)
                self._alias_combo.setCurrentIndex(0)
                self._alias_combo.blockSignals(False)
                return

        self.appState.process_profiles_from_collections()
        self.devices_changed.emit()
        # Refresh list to update status dots
        self.refresh()

    def _on_template_change(self):
        if not self._selected_guid:
            return

        default_dir = os.path.join(install_root(), "templates")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SVG Template",
            default_dir,
            "SVG Files (*.svg)",
        )

        if file_path:
            add_update_device_template_path(self._selected_guid, file_path)
            self.devices_changed.emit()
            self.refresh()

    def _on_template_clear(self):
        if not self._selected_guid:
            return

        remove_template_path_from_device(self._selected_guid)
        self.devices_changed.emit()
        self.refresh()

    def _on_visibility_changed(self, state: int):
        if not self._selected_guid:
            return

        all_devices = self._get_all_known_devices()
        device_name = next(
            (n for g, n in all_devices if g == self._selected_guid),
            self._selected_guid,
        )

        is_visible = state == Qt.CheckState.Checked.value
        self.appState.device_service.set_hidden(
            self._selected_guid, device_name, not is_visible
        )
        self.devices_changed.emit()
        # Refresh list to update dimmed/hidden styling
        self.refresh()


if __name__ == "__main__":
    pass
