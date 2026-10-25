""" "Add modifier boxes automatically" (plan §5.4 auto-add, mock wording).

The dialog plans with ``plan_for_render`` on every change and shows a live
"What will happen" summary; nothing is written until the caller applies
``result_ops()`` (one undo step on the Layout screen).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.render.auto_layout import (
    AutoAddResult,
    PlanOptions,
    counts_from_device,
)
from joystick_diagrams.render.layout import DEFAULT_MAX_BOXES
from joystick_diagrams.ui import strings_layout as S
from joystick_diagrams.ui.layout_editor.planning import (
    counts_for_devices,
    plan_for_render,
)

ARRANGEMENTS: tuple[tuple[str, str], ...] = (
    ("auto", S.AUTO_WHERE_AUTO),
    ("below", S.AUTO_WHERE_BELOW),
    ("right", S.AUTO_WHERE_RIGHT),
    ("left", S.AUTO_WHERE_LEFT),
    ("above", S.AUTO_WHERE_ABOVE),
)
MAX_BOXES_LIMIT = 8
HEADING_STYLE = (
    "color: #E8EAED; font-size: 13px; font-weight: bold; background: transparent;"
)
HELP_STYLE = "color: #9AA0A6; font-size: 12px; background: transparent;"
OK_STYLE = "color: #34D399; font-size: 12px; background: transparent;"
WARN_STYLE = "color: #F59E0B; font-size: 12px; background: transparent;"
SUMMARY_STYLE = (
    "QFrame#summary_frame { background: #2c2f38; border: 1px solid #3C4043; "
    "border-radius: 6px; }"
)


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(HEADING_STYLE)
    return label


def _line(style: str = HELP_STYLE) -> QLabel:
    label = QLabel("")
    label.setWordWrap(True)
    label.setStyleSheet(style)
    return label


class AutoAddDialog(QDialog):
    def __init__(
        self,
        *,
        scene: Any,
        render: Any,
        export_device: Any,
        all_devices: list[Any],
        scope_text: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(S.AUTO_TITLE)
        self.setMinimumWidth(600)
        self._scene = scene
        self._render = render
        self._device = export_device.device
        self._profile_name = export_device.profile_wrapper.profile_name
        self._all_devices = all_devices or [self._device]
        self._scope_text = scope_text
        self._result: AutoAddResult = AutoAddResult()
        self._build()
        self.recompute()

    # ── UI ──

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(_heading(S.AUTO_WHICH))
        self.which_group = QButtonGroup(self)
        self.which_this = QRadioButton(
            S.AUTO_WHICH_THIS_PROFILE.format(profile=self._profile_name)
        )
        any_count = len(counts_for_devices(self._all_devices, MAX_BOXES_LIMIT))
        self.which_any = QRadioButton(S.AUTO_WHICH_ANY_PROFILE.format(count=any_count))
        self.which_this.setChecked(True)
        self.which_group.addButton(self.which_this, 0)
        self.which_group.addButton(self.which_any, 1)
        layout.addWidget(self.which_this)
        layout.addWidget(self.which_any)

        layout.addWidget(_heading(S.AUTO_HOW_MANY))
        row = QHBoxLayout()
        hint = QLabel(S.AUTO_HOW_MANY_HINT)
        hint.setStyleSheet(HELP_STYLE)
        row.addWidget(hint)
        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, MAX_BOXES_LIMIT)
        self.max_spin.setValue(DEFAULT_MAX_BOXES)
        self.max_spin.setAccessibleName(S.AUTO_HOW_MANY)
        self.max_spin.setProperty("class", "view-binds-list")
        row.addWidget(self.max_spin)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addWidget(_heading(S.AUTO_WHERE))
        self.where_combo = QComboBox()
        self.where_combo.setProperty("class", "view-binds-list")
        self.where_combo.setAccessibleName(S.AUTO_WHERE)
        for value, text in ARRANGEMENTS:
            self.where_combo.addItem(text, value)
        layout.addWidget(self.where_combo)

        layout.addWidget(_heading(S.AUTO_NO_ROOM))
        self.room_group = QButtonGroup(self)
        self.room_list = QRadioButton(S.AUTO_NO_ROOM_LIST)
        self.room_notice = QRadioButton(S.AUTO_NO_ROOM_NOTICE)
        self.room_list.setChecked(True)
        self.room_group.addButton(self.room_list, 0)
        self.room_group.addButton(self.room_notice, 1)
        layout.addWidget(self.room_list)
        layout.addWidget(self.room_notice)

        summary = QFrame()
        summary.setObjectName("summary_frame")
        summary.setStyleSheet(SUMMARY_STYLE)
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(10, 8, 10, 8)
        summary_layout.setSpacing(4)
        summary_layout.addWidget(_heading(S.AUTO_SUMMARY_HEADING))
        self.summary_added = _line(OK_STYLE)
        self.summary_room = _line(WARN_STYLE)
        self.summary_room_tail = _line()
        self.summary_display = _line()
        self.summary_applies = _line()
        for label in (
            self.summary_added,
            self.summary_room,
            self.summary_room_tail,
            self.summary_display,
            self.summary_applies,
        ):
            label.setWordWrap(False)
            summary_layout.addWidget(label)
        layout.addWidget(summary)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QPushButton(S.AUTO_CANCEL)
        self.cancel_button.setProperty("class", "plugin-setup-button")
        self.cancel_button.clicked.connect(self.reject)
        self.add_button = QPushButton(S.AUTO_ADD_NONE)
        self.add_button.setProperty("class", "run-button")
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self.accept)
        self.add_button.setDefault(True)
        self.add_button.setMaximumWidth(220)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.add_button)
        layout.addLayout(buttons)

        self.which_group.idToggled.connect(lambda _i, _c: self.recompute())
        self.max_spin.valueChanged.connect(lambda _v: self.recompute())
        self.where_combo.currentIndexChanged.connect(lambda _i: self.recompute())
        self.room_group.idToggled.connect(lambda _i, _c: self.recompute())

    # ── Planning ──

    def counts(self) -> dict[str, int]:
        limit = self.max_spin.value()
        if self.which_any.isChecked():
            return counts_for_devices(self._all_devices, limit)
        return counts_from_device(self._device, limit)

    def options(self) -> PlanOptions:
        return PlanOptions(
            arrangement=self.where_combo.currentData() or "auto",
            max_count=self.max_spin.value(),
        )

    def recompute(self) -> None:
        counts = self.counts()
        self._result = plan_for_render(
            self._scene, self._render, counts, self.options()
        )
        boxes = len(self._result.placed)
        controls = len({box.target for box in self._result.placed})
        unplaced = [u for u in self._result.unplaced if u.reason == "no_space"]
        no_room_controls = len({u.target for u in unplaced})
        if not counts:
            self.summary_added.setText(
                S.AUTO_SUMMARY_NO_CONTROLS.format(profile=self._profile_name)
            )
            self.summary_added.setStyleSheet(HELP_STYLE)
        elif boxes == 0:
            self.summary_added.setText(
                S.AUTO_SUMMARY_NONE_FIT if unplaced else S.AUTO_SUMMARY_NOTHING
            )
            self.summary_added.setStyleSheet(HELP_STYLE)
        else:
            self.summary_added.setText(
                "✓ "
                + S.AUTO_SUMMARY_ADDED.format(
                    boxes=boxes,
                    es=S.plural(boxes, "", "es"),
                    controls=controls,
                    s=S.plural(controls),
                )
            )
            self.summary_added.setStyleSheet(OK_STYLE)
        if unplaced:
            self.summary_room.setText(
                "! "
                + S.AUTO_SUMMARY_NO_ROOM.format(
                    controls=no_room_controls,
                    s=S.plural(no_room_controls),
                    dont=S.plural(no_room_controls, "doesn't", "don't"),
                    boxes=len(unplaced),
                    es=S.plural(len(unplaced), "", "es"),
                )
            )
            self.summary_room_tail.setText(
                S.AUTO_SUMMARY_NO_ROOM_LISTED
                if self.room_list.isChecked()
                else S.AUTO_SUMMARY_NO_ROOM_NOTICE
            )
        self.summary_room.setVisible(bool(unplaced))
        self.summary_room_tail.setVisible(bool(unplaced))
        self.summary_display.setVisible(bool(unplaced) and self.room_list.isChecked())
        self.summary_display.setText(S.AUTO_SUMMARY_DISPLAY_CHANGE)
        self.summary_applies.setText(
            S.AUTO_SUMMARY_APPLIES.format(scope=self._scope_text)
        )
        self.add_button.setEnabled(boxes > 0)
        self.add_button.setText(
            S.AUTO_ADD_N.format(count=boxes, es=S.plural(boxes, "", "es"))
            if boxes
            else S.AUTO_ADD_NONE
        )
        self.layout().activate()
        self.adjustSize()

    # ── Results ──

    def result_ops(self) -> list:
        return list(self._result.ops)

    def planned(self) -> AutoAddResult:
        return self._result

    def list_extras_under_text(self) -> bool:
        return self.room_list.isChecked() and any(
            u.reason == "no_space" for u in self._result.unplaced
        )


if __name__ == "__main__":
    pass
