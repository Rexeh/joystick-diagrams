"""3. Bindings › Shared bindings: let one profile use another's bindings.

Wraps ``parent_profiles.parent_profile_ui`` (the ordered list of profiles this
profile uses bindings from) and hosts the clash rule that used to live in
Settings › General, the only place where it has an effect: "If a profile and
the one it uses both bind a control". Changing it reprocesses the profiles.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.conflict_strategy import (
    INHERITANCE_CONFLICT_STRATEGY_KEY,
    InheritanceConflictStrategy,
    get_inheritance_strategy,
)
from joystick_diagrams.db.db_settings import add_update_setting_value
from joystick_diagrams.ui import parent_profiles
from joystick_diagrams.ui import strings_bindings as S

_logger = logging.getLogger(__name__)

CLASH_OPTIONS: tuple[tuple[InheritanceConflictStrategy, str], ...] = (
    (InheritanceConflictStrategy.KEEP_EXISTING, S.CLASH_KEEP),
    (InheritanceConflictStrategy.CONCATENATE, S.CLASH_CONCATENATE),
    (InheritanceConflictStrategy.MODIFIER, S.CLASH_MODIFIER),
)


class CustomiseInheritance(QWidget):
    bindings_changed = Signal()  # parents or the clash rule changed

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.appState = AppState()
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        help_text = QLabel(
            S.SHARED_INTRO
            + f' <a href="{S.SHARED_LEARN_MORE_URL}" style="color: #8AB4F8;">'
            + f"{S.SHARED_LEARN_MORE}</a>"
        )
        help_text.setObjectName("device_help_label")
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_text.setOpenExternalLinks(True)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
        selector_label = QLabel(S.SHARED_PROFILE)
        selector_label.setStyleSheet("font-weight: bold;")
        selector_row.addWidget(selector_label)
        self.profile_combo = QComboBox()
        self.profile_combo.setProperty("class", "view-binds-list")
        self.profile_combo.setAccessibleName(S.SHARED_PROFILE)
        self.profile_combo.setMaxVisibleItems(15)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        selector_row.addWidget(self.profile_combo, stretch=1)
        layout.addLayout(selector_row)

        self.parent_widget = parent_profiles.parent_profile_ui()
        self.parent_widget.label.setText(S.USES_BINDINGS_FROM)
        self.parent_widget.label_2.setText(S.USES_BINDINGS_FROM_HELP)
        self.parent_widget.addParentItem.setText(S.ADD_SHARED_PROFILE)
        self.parent_widget.parentProfileChange.connect(self.bindings_changed.emit)
        layout.addWidget(self.parent_widget)

        # The clash rule (moved here from Settings › General)
        clash_row = QHBoxLayout()
        clash_row.setSpacing(8)
        clash_label = QLabel(S.CLASH_LABEL)
        clash_label.setObjectName("device_help_label")
        clash_label.setWordWrap(True)
        clash_row.addWidget(clash_label, 1)
        self.clash_combo = QComboBox()
        self.clash_combo.setProperty("class", "view-binds-list")
        self.clash_combo.setAccessibleName(S.CLASH_LABEL)
        self.clash_combo.setMinimumWidth(300)
        for value, label in CLASH_OPTIONS:
            self.clash_combo.addItem(label, value.value)
        self.clash_combo.currentIndexChanged.connect(self._on_clash_changed)
        clash_row.addWidget(self.clash_combo)
        layout.addLayout(clash_row)

        layout.addStretch()
        self._load_clash()

    # ── Refresh ──

    def refresh(self):
        """Rebuild the profile selector from current app state (keeps the selection)."""
        current = self.current_profile_key()
        self._loading = True
        try:
            self.profile_combo.clear()
            for wrapper in self.appState.profile_wrappers:
                self.profile_combo.addItem(
                    QIcon(wrapper.profile_origin.icon),
                    f"{wrapper.profile_origin.name} / {wrapper.profile_name}",
                    wrapper,
                )
        finally:
            self._loading = False
        self._load_clash()
        if self.profile_combo.count() == 0:
            return
        index = self._index_of(current) if current else -1
        self.profile_combo.setCurrentIndex(max(index, 0))
        self._on_profile_changed(self.profile_combo.currentIndex())

    def _index_of(self, profile_key: str) -> int:
        for index in range(self.profile_combo.count()):
            wrapper = self.profile_combo.itemData(index, Qt.ItemDataRole.UserRole)
            if wrapper is not None and wrapper.profile_key == profile_key:
                return index
        return -1

    def current_profile_key(self) -> str | None:
        wrapper = self.profile_combo.currentData(Qt.ItemDataRole.UserRole)
        return wrapper.profile_key if wrapper is not None else None

    def select_profile(self, profile_key: str | None) -> None:
        """Open on ``profile_key`` (the profile selected on the Bindings screen)."""
        if not profile_key:
            return
        index = self._index_of(profile_key)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

    def _on_profile_changed(self, index: int):
        if self._loading:
            return
        wrapper = self.profile_combo.currentData(Qt.ItemDataRole.UserRole)
        if wrapper:
            self.parent_widget.set_profile_parent_map(wrapper)

    # ── Clash rule ──

    def _load_clash(self) -> None:
        self._loading = True
        try:
            current = get_inheritance_strategy()
            index = self.clash_combo.findData(current.value)
            self.clash_combo.setCurrentIndex(max(index, 0))
        finally:
            self._loading = False

    def current_clash(self) -> InheritanceConflictStrategy:
        return InheritanceConflictStrategy(self.clash_combo.currentData())

    def _on_clash_changed(self, index: int) -> None:
        if self._loading:
            return
        value = self.clash_combo.currentData()
        if not value:
            return
        add_update_setting_value(INHERITANCE_CONFLICT_STRATEGY_KEY, value)
        self.appState.reprocess_profiles_with_notice(S.CLASH_SAVED)
        self.bindings_changed.emit()


if __name__ == "__main__":
    pass
