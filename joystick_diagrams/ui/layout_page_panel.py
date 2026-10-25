"""4. Diagrams › Layout, page mode: the right-hand **Page** panel.

Shown instead of the box panel when the Diagram picker selects a page
("▣ <page>"). It edits the fields the ``Page`` model already has: name, the
controllers on the page (read-only list; "Change controllers…" opens the
Combine dialog), which profiles it is made for (with live counts), the
arrangement, page size and orientation, scale, gap, title and date, and Reset to
defaults. It never saves by itself: every change is emitted as ``edited`` with
the changed fields and ``CustomiseLayout`` saves it through ``PageService``,
records one undo step and re-renders the preview.

Free placement of the panels and page notes stay for v2 (the model already
stores ``Placement.x_mm``/``y_mm`` and ``Page.notes``).

``PageHistory`` is the page-mode undo stack: one ``(before, after)`` pair of
``Page`` snapshots per change.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.render.page import (
    MIN_LEGIBLE_PT,
    Arrangement,
    Orientation,
    Page,
    ProfileRule,
    SizePreset,
)
from joystick_diagrams.ui import strings_diagrams as D
from joystick_diagrams.ui import strings_layout as S
from joystick_diagrams.ui.layout_editor.panel_style import (
    LABEL_STYLE,
    MUTED_STYLE,
    NOTICE_STYLE,
    heading_label,
    help_label,
    panel_button,
)
from joystick_diagrams.ui.pages_dialog import (
    ARRANGEMENTS,
    ORIENTATIONS,
    SCALE_MAX,
    SCALE_MIN,
    SIZES,
)

GAP_MAX_MM = 50.0
CUSTOM_DEFAULT_MM = (210.0, 297.0)
GUID_ROLE = Qt.ItemDataRole.UserRole
# What Reset to defaults puts back (name, controllers, the profile rule and the
# export choice are the player's decisions, not looks, and are kept).
RESET_FIELDS = (
    "size_preset",
    "width_mm",
    "height_mm",
    "orientation",
    "arrangement",
    "gap_mm",
    "margin_mm",
    "scale",
    "title",
    "show_title",
    "show_date",
)
SCALE_HIGHLIGHT_STYLE = (
    "QFrame#page_scale_frame { background: rgba(245, 158, 11, 0.12); "
    "border: 1px solid #F59E0B; border-radius: 6px; }"
)
SCALE_PLAIN_STYLE = "QFrame#page_scale_frame { border: 1px solid transparent; }"
WARNING_STYLE = "color: #FBBF24; font-size: 12px; background: transparent;"
# compose_page's legibility sentence: "Text on <controller> prints at 4.8 pt. …"
LEGIBILITY_MARK = " prints at "
ERROR_STYLE = "color: #F87171; font-size: 12px; background: transparent;"


def default_update(page: Page) -> dict:
    """The fields Reset to defaults changes, with every placement back on the
    arrangement at its normal size."""
    defaults = Page(name=page.name)
    update = {key: getattr(defaults, key) for key in RESET_FIELDS}
    update["placements"] = [
        placement.model_copy(update={"x_mm": None, "y_mm": None, "scale": 1.0})
        for placement in page.placements
    ]
    return update


def same_page(a: Page, b: Page) -> bool:
    """Equal apart from the saved-at stamp."""
    return a.model_dump(exclude={"updated_at"}) == b.model_dump(exclude={"updated_at"})


def arrangement_parts(text: str) -> tuple[str, str]:
    """ "Side by side — left to right in one row" → ("Side by side", "left to …")."""
    name, _sep, description = text.partition(" — ")
    return name, description


class PageHistory:
    """Undo/redo for one page: each change is a ``(before, after)`` snapshot."""

    def __init__(self, page_id: str):
        self.page_id = page_id
        self._undo: list[tuple[Page, Page]] = []
        self._redo: list[tuple[Page, Page]] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def record(self, before: Page, after: Page) -> None:
        self._undo.append((before, after))
        self._redo.clear()

    def undo(self) -> Page | None:
        if not self._undo:
            return None
        step = self._undo.pop()
        self._redo.append(step)
        return step[0]

    def redo(self) -> Page | None:
        if not self._redo:
            return None
        step = self._redo.pop()
        self._undo.append(step)
        return step[1]


class _ClickLabel(QLabel):
    """A wrapping label that toggles its radio button when clicked."""

    clicked = Signal()

    def mousePressEvent(self, event):  # noqa: N802
        self.clicked.emit()
        super().mousePressEvent(event)


def _wrapping_radio(text: str, detail: str = "") -> tuple[QWidget, QRadioButton]:
    """A radio button whose text wraps in the narrow panel (QRadioButton can't)."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    radio = QRadioButton()
    radio.setAccessibleName(f"{text} {detail}".strip())
    layout.addWidget(radio, 0, Qt.AlignmentFlag.AlignTop)
    labels = QVBoxLayout()
    labels.setContentsMargins(0, 1, 0, 0)
    labels.setSpacing(0)
    label = _ClickLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(LABEL_STYLE)
    label.clicked.connect(radio.click)
    labels.addWidget(label)
    if detail:
        sub = _ClickLabel(detail)
        sub.setWordWrap(True)
        sub.setStyleSheet(MUTED_STYLE)
        sub.clicked.connect(radio.click)
        labels.addWidget(sub)
    layout.addLayout(labels, 1)
    radio.text_label = label  # type: ignore[attr-defined] - tests and updates
    return row, radio


def _field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(LABEL_STYLE + " font-weight: bold;")
    return label


class PagePanel(QWidget):
    """The Page panel. ``load()`` fills it; user changes come out as signals."""

    edited = Signal(object)  # dict of the changed Page fields (object: Qt keeps enums)
    change_controllers_requested = Signal()
    edit_controller_requested = Signal(str)  # device guid
    reset_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._page: Page | None = None
        self._loading = False
        self._names: dict[str, str] = {}
        self._build()

    # ── Construction ──

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(heading_label(S.PAGE_PANEL_HEADING))

        layout.addWidget(_field_label(S.PAGE_NAME))
        self.name_edit = QLineEdit()
        self.name_edit.setAccessibleName(S.PAGE_NAME)
        self.name_edit.editingFinished.connect(self._on_name_finished)
        layout.addWidget(self.name_edit)
        self.problem_label = QLabel("")
        self.problem_label.setWordWrap(True)
        self.problem_label.setStyleSheet(ERROR_STYLE)
        self.problem_label.hide()
        layout.addWidget(self.problem_label)

        # ── The controllers on this page ──
        layout.addSpacing(4)
        layout.addWidget(_field_label(S.PAGE_CONTROLLERS))
        self.controller_list = QListWidget()
        self.controller_list.setAccessibleName(S.PAGE_CONTROLLERS)
        self.controller_list.setProperty("class", "view-binds-list")
        self.controller_list.setToolTip(S.PAGE_CONTROLLERS_HELP)
        self.controller_list.currentItemChanged.connect(
            lambda *_args: self._update_selection()
        )
        layout.addWidget(self.controller_list)
        self.change_controllers_button = panel_button(S.PAGE_CHANGE_CONTROLLERS)
        self.change_controllers_button.clicked.connect(
            self.change_controllers_requested.emit
        )
        layout.addWidget(self.change_controllers_button)

        self.selection_box = QFrame()
        self.selection_box.setObjectName("notice_frame")
        self.selection_box.setStyleSheet(NOTICE_STYLE)
        selection = QVBoxLayout(self.selection_box)
        selection.setContentsMargins(8, 6, 8, 8)
        selection.setSpacing(4)
        self.selection_title = heading_label("")
        selection.addWidget(self.selection_title)
        selection.addWidget(help_label(S.PAGE_CONTROLLER_PLACED))
        self.edit_boxes_button = panel_button(S.PAGE_EDIT_CONTROLLER_BOXES)
        self.edit_boxes_button.setToolTip(S.PAGE_EDIT_CONTROLLER_BOXES_TIP)
        self.edit_boxes_button.clicked.connect(self._on_edit_boxes)
        selection.addWidget(self.edit_boxes_button)
        self.selection_box.hide()
        layout.addWidget(self.selection_box)

        # ── Make this page for ──
        layout.addSpacing(4)
        layout.addWidget(_field_label(D.COMBINE_MAKE_FOR))
        self.rule_group = QButtonGroup(self)
        shared_row, self.rule_shared = _wrapping_radio("")
        any_row, self.rule_any = _wrapping_radio("", D.RULE_ANY_HELP)
        for index, (row, radio) in enumerate(
            ((shared_row, self.rule_shared), (any_row, self.rule_any))
        ):
            self.rule_group.addButton(radio, index)
            layout.addWidget(row)
        self.rule_group.idToggled.connect(self._on_rule_toggled)

        # ── Arrangement ──
        layout.addSpacing(4)
        layout.addWidget(_field_label(S.PAGE_ARRANGEMENT))
        self.arrangement_group = QButtonGroup(self)
        self.arrangement_buttons: dict[Arrangement, QRadioButton] = {}
        for index, (value, text) in enumerate(ARRANGEMENTS):
            name, description = arrangement_parts(text)
            row, radio = _wrapping_radio(name, description)
            self.arrangement_group.addButton(radio, index)
            self.arrangement_buttons[value] = radio
            layout.addWidget(row)
        self.arrangement_group.idToggled.connect(self._on_arrangement_toggled)

        # ── Page size and orientation ──
        layout.addSpacing(4)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        grid.addWidget(_field_label(S.PAGE_SIZE), 0, 0)
        grid.addWidget(_field_label(S.PAGE_ORIENTATION), 0, 1)
        self.size_combo = QComboBox()
        self.size_combo.setProperty("class", "view-binds-list")
        self.size_combo.setAccessibleName(S.PAGE_SIZE)
        for value, text in SIZES:
            self.size_combo.addItem(text, value.value)
        self.size_combo.currentIndexChanged.connect(self._on_size_changed)
        grid.addWidget(self.size_combo, 1, 0)
        self.orientation_combo = QComboBox()
        self.orientation_combo.setProperty("class", "view-binds-list")
        self.orientation_combo.setAccessibleName(S.PAGE_ORIENTATION)
        for value, text in zip(ORIENTATIONS, D.ORIENTATION_CHOICES, strict=True):
            self.orientation_combo.addItem(text, value.value)
        self.orientation_combo.currentIndexChanged.connect(self._on_orientation)
        grid.addWidget(self.orientation_combo, 1, 1)
        layout.addLayout(grid)

        self.custom_widget = QWidget()
        custom = QGridLayout(self.custom_widget)
        custom.setContentsMargins(0, 0, 0, 0)
        custom.setHorizontalSpacing(8)
        self.width_spin = self._mm_spin(D.SIZE_CUSTOM_WIDTH, 2000.0)
        self.height_spin = self._mm_spin(D.SIZE_CUSTOM_HEIGHT, 2000.0)
        for column, (text, spin) in enumerate(
            (
                (D.SIZE_CUSTOM_WIDTH, self.width_spin),
                (D.SIZE_CUSTOM_HEIGHT, self.height_spin),
            )
        ):
            label = QLabel(text)
            label.setStyleSheet(LABEL_STYLE)
            custom.addWidget(label, 0, column)
            custom.addWidget(spin, 1, column)
        self.width_spin.valueChanged.connect(
            lambda value: self._emit_if_changed("width_mm", value)
        )
        self.height_spin.valueChanged.connect(
            lambda value: self._emit_if_changed("height_mm", value)
        )
        self.custom_widget.hide()
        layout.addWidget(self.custom_widget)

        # ── Scale (highlighted when text prints too small) ──
        layout.addSpacing(4)
        self.scale_frame = QFrame()
        self.scale_frame.setObjectName("page_scale_frame")
        self.scale_frame.setStyleSheet(SCALE_PLAIN_STYLE)
        scale_box = QVBoxLayout(self.scale_frame)
        scale_box.setContentsMargins(6, 4, 6, 6)
        scale_box.setSpacing(4)
        scale_head = QHBoxLayout()
        scale_head.addWidget(_field_label(S.PAGE_SCALE))
        scale_head.addStretch(1)
        self.scale_label = QLabel(S.PAGE_SCALE_VALUE.format(percent=SCALE_MAX))
        self.scale_label.setStyleSheet(LABEL_STYLE)
        scale_head.addWidget(self.scale_label)
        scale_box.addLayout(scale_head)
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(SCALE_MIN, SCALE_MAX)
        self.scale_slider.setPageStep(5)
        self.scale_slider.setAccessibleName(S.PAGE_SCALE)
        self.scale_slider.setToolTip(S.PAGE_SCALE_TIP)
        self.scale_slider.valueChanged.connect(self._on_scale_moved)
        self.scale_slider.sliderReleased.connect(self._commit_scale)
        scale_box.addWidget(self.scale_slider)
        self.legibility_label = QLabel("")
        self.legibility_label.setWordWrap(True)
        self.legibility_label.setStyleSheet(WARNING_STYLE)
        self.legibility_label.hide()
        scale_box.addWidget(self.legibility_label)
        layout.addWidget(self.scale_frame)

        gap_row = QHBoxLayout()
        gap_label = _field_label(S.PAGE_GAP)
        gap_label.setToolTip(S.PAGE_GAP_TIP)
        gap_row.addWidget(gap_label)
        gap_row.addStretch(1)
        self.gap_spin = self._mm_spin(S.PAGE_GAP, GAP_MAX_MM)
        self.gap_spin.setToolTip(S.PAGE_GAP_TIP)
        self.gap_spin.valueChanged.connect(
            lambda value: self._emit_if_changed("gap_mm", value)
        )
        gap_row.addWidget(self.gap_spin)
        layout.addLayout(gap_row)

        # ── Title and date ──
        layout.addSpacing(4)
        layout.addWidget(_field_label(S.PAGE_TITLE_AND_DATE))
        checks = QHBoxLayout()
        self.show_title_check = QCheckBox(S.PAGE_SHOW_TITLE)
        self.show_title_check.toggled.connect(
            lambda on: self._emit_if_changed("show_title", on)
        )
        self.show_date_check = QCheckBox(S.PAGE_SHOW_DATE)
        self.show_date_check.toggled.connect(
            lambda on: self._emit_if_changed("show_date", on)
        )
        checks.addWidget(self.show_title_check)
        checks.addWidget(self.show_date_check)
        checks.addStretch(1)
        layout.addLayout(checks)
        title_label = QLabel(S.PAGE_TITLE)
        title_label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(title_label)
        self.title_edit = QLineEdit()
        self.title_edit.setAccessibleName(S.PAGE_TITLE)
        self.title_edit.setClearButtonEnabled(True)
        self.title_edit.editingFinished.connect(self._on_title_finished)
        layout.addWidget(self.title_edit)

        layout.addSpacing(4)
        self.reset_button = panel_button(S.PAGE_RESET)
        self.reset_button.setToolTip(S.PAGE_RESET_TIP)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        layout.addWidget(self.reset_button)

        # ── Notices from the last render ──
        layout.addSpacing(8)
        layout.addWidget(heading_label(S.PANEL_NOTICES))
        self.notices_box = QVBoxLayout()
        self.notices_box.setSpacing(6)
        layout.addLayout(self.notices_box)
        self.no_notices = help_label(S.PANEL_NO_NOTICES)
        layout.addWidget(self.no_notices)
        layout.addStretch(1)
        layout.addWidget(help_label(S.PANEL_UNDO_NOTE))

    @staticmethod
    def _mm_spin(name: str, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, maximum)
        spin.setDecimals(1)
        spin.setSingleStep(1.0)
        spin.setAccessibleName(name)
        spin.setKeyboardTracking(False)
        spin.setProperty("class", "view-binds-list")
        spin.setMaximumWidth(96)
        return spin

    # ── Filling ──

    @property
    def page(self) -> Page | None:
        return self._page

    def load(
        self,
        page: Page,
        names: dict[str, str],
        counts: dict[ProfileRule, int],
        profile_name: str = "",
    ) -> None:
        """Show ``page``; ``counts`` is how many profiles each rule makes it for."""
        self._page = page
        self._names = dict(names)
        self._loading = True
        try:
            if not self.name_edit.hasFocus() or self.name_edit.text() != page.name:
                self.name_edit.setText(page.name)
            selected = self.selected_controller()
            self.controller_list.clear()
            for guid in page.member_guids:
                item = QListWidgetItem(names.get(guid, guid))
                item.setData(GUID_ROLE, guid)
                self.controller_list.addItem(item)
                if guid == selected:
                    self.controller_list.setCurrentItem(item)
            rows = min(max(self.controller_list.count(), 1), 5)
            row_height = max(self.controller_list.sizeHintForRow(0), 24)
            frame = 2 * self.controller_list.frameWidth()
            self.controller_list.setFixedHeight(rows * row_height + frame + 6)
            self._set_rule_texts(page, counts)
            (
                self.rule_any
                if page.profile_rule is ProfileRule.ANY
                else self.rule_shared
            ).setChecked(True)
            self.arrangement_buttons[page.arrangement].setChecked(True)
            self.size_combo.setCurrentIndex(
                max(self.size_combo.findData(page.size_preset.value), 0)
            )
            self.orientation_combo.setCurrentIndex(
                max(self.orientation_combo.findData(page.orientation.value), 0)
            )
            self.orientation_combo.setEnabled(page.size_preset is not SizePreset.FIT)
            custom = page.size_preset is SizePreset.CUSTOM
            self.custom_widget.setVisible(custom)
            if custom:
                self.width_spin.setValue(page.width_mm or 0.0)
                self.height_spin.setValue(page.height_mm or 0.0)
            percent = round(min(max(page.scale, SCALE_MIN / 100), 1.0) * 100)
            if not self.scale_slider.isSliderDown():
                self.scale_slider.setValue(percent)
            self.scale_label.setText(
                S.PAGE_SCALE_VALUE.format(percent=self.scale_slider.value())
            )
            self.gap_spin.setValue(page.gap_mm)
            self.show_title_check.setChecked(page.show_title)
            self.show_date_check.setChecked(page.show_date)
            self.title_edit.setText(page.title or "")
            self.title_edit.setEnabled(page.show_title)
            self.set_profile_name(profile_name)
        finally:
            self._loading = False
        self._update_selection()

    def set_profile_name(self, profile_name: str) -> None:
        """The example in the custom title's placeholder follows Preview with."""
        if self._page is None:
            return
        example = f"{profile_name or S.PAGE_TITLE_EXAMPLE_PROFILE} · {self._page.name}"
        self.title_edit.setPlaceholderText(
            S.PAGE_TITLE_PLACEHOLDER.format(example=example)
        )

    def _set_rule_texts(self, page: Page, counts: dict[ProfileRule, int]) -> None:
        members = len(page.member_guids)
        controllers = (
            D.RULE_BOTH_CONTROLLERS
            if members == 2
            else D.RULE_ALL_CONTROLLERS.format(count=max(members, 2))
        )
        shared = D.RULE_SHARED.format(
            controllers=controllers,
            profiles=D.counted(counts.get(ProfileRule.SHARED, 0), D.PROFILES),
        )
        anyone = D.RULE_ANY.format(
            profiles=D.counted(counts.get(ProfileRule.ANY, 0), D.PROFILES)
        )
        self.rule_shared.text_label.setText(shared)  # type: ignore[attr-defined]
        self.rule_shared.setAccessibleName(shared)
        self.rule_any.text_label.setText(anyone)  # type: ignore[attr-defined]
        self.rule_any.setAccessibleName(f"{anyone} {D.RULE_ANY_HELP}")

    def set_problem(self, text: str) -> None:
        self.problem_label.setText(text)
        self.problem_label.setVisible(bool(text))

    def set_compose_result(self, result: Any) -> None:
        """Notices from the last render. When text prints too small, compose's
        own sentence ("Text on … prints at 4.8 pt. …") sits in the Scale box,
        which is highlighted as the fix; other warnings are listed as notices."""
        self._clear_notices()
        warnings = list(getattr(result, "warnings", ()) or ())
        min_pt = getattr(result, "min_font_pt", None)
        small = min_pt is not None and min_pt < MIN_LEGIBLE_PT
        legibility = [w for w in warnings if LEGIBILITY_MARK in w] if small else []
        others = [w for w in warnings if w not in legibility]
        self.scale_frame.setStyleSheet(
            SCALE_HIGHLIGHT_STYLE if small else SCALE_PLAIN_STYLE
        )
        self.scale_frame.setProperty("highlighted", small)
        if small:
            at_full = self.scale_slider.value() >= SCALE_MAX
            fix = S.PAGE_FIX_AT_FULL_SCALE if at_full else S.PAGE_FIX_SCALE
            self.legibility_label.setText("\n".join([*legibility, fix]))
        self.legibility_label.setVisible(small)
        for text in others:
            frame = QFrame()
            frame.setObjectName("notice_frame")
            frame.setStyleSheet(NOTICE_STYLE)
            row = QVBoxLayout(frame)
            row.setContentsMargins(8, 6, 8, 6)
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(LABEL_STYLE)
            row.addWidget(label)
            self.notices_box.addWidget(frame)
        self.no_notices.setVisible(not others)

    def notice_texts(self) -> list[str]:
        texts = []
        for index in range(self.notices_box.count()):
            frame = self.notices_box.itemAt(index).widget()
            label = frame.findChild(QLabel) if frame is not None else None
            if label is not None:
                texts.append(label.text())
        return texts

    def _clear_notices(self) -> None:
        while self.notices_box.count():
            item = self.notices_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    # ── Selection of a controller ──

    def selected_controller(self) -> str | None:
        item = self.controller_list.currentItem()
        return item.data(GUID_ROLE) if item is not None else None

    def select_controller(self, guid: str | None) -> None:
        for row in range(self.controller_list.count()):
            item = self.controller_list.item(row)
            if item.data(GUID_ROLE) == guid:
                self.controller_list.setCurrentItem(item)
                return
        self.controller_list.setCurrentItem(None)

    def _update_selection(self) -> None:
        guid = self.selected_controller()
        self.selection_box.setVisible(guid is not None)
        if guid is not None:
            self.selection_title.setText(self._names.get(guid, guid))

    def _on_edit_boxes(self) -> None:
        guid = self.selected_controller()
        if guid:
            self.edit_controller_requested.emit(guid)

    # ── Reactions ──

    def _emit(self, update: dict) -> None:
        if self._loading or self._page is None:
            return
        self.edited.emit(update)

    def _emit_if_changed(self, field: str, value: Any) -> None:
        if self._page is None or self._loading:
            return
        current = getattr(self._page, field)
        if isinstance(value, float) and current is not None:
            if abs(float(current) - value) < 1e-6:
                return
        elif current == value:
            return
        self._emit({field: value})

    def _on_name_finished(self) -> None:
        if self._page is not None and self.name_edit.text() != self._page.name:
            self._emit({"name": self.name_edit.text()})

    def _on_title_finished(self) -> None:
        if self._page is None:
            return
        title = " ".join(self.title_edit.text().split()) or None
        if title != self._page.title:
            self._emit({"title": title})

    def _on_rule_toggled(self, button_id: int, checked: bool) -> None:
        if checked:
            rule = ProfileRule.ANY if button_id == 1 else ProfileRule.SHARED
            self._emit_if_changed("profile_rule", rule)

    def _on_arrangement_toggled(self, button_id: int, checked: bool) -> None:
        if checked:
            self._emit_if_changed("arrangement", ARRANGEMENTS[button_id][0])

    def _on_size_changed(self, _index: int) -> None:
        if self._loading or self._page is None:
            return
        size = SizePreset(self.size_combo.currentData())
        if size is self._page.size_preset:
            return
        update: dict = {"size_preset": size, "width_mm": None, "height_mm": None}
        if size is SizePreset.CUSTOM:
            width, height = CUSTOM_DEFAULT_MM
            update["width_mm"] = self._page.width_mm or width
            update["height_mm"] = self._page.height_mm or height
        self._emit(update)

    def _on_orientation(self, _index: int) -> None:
        self._emit_if_changed(
            "orientation", Orientation(self.orientation_combo.currentData())
        )

    def _on_scale_moved(self, value: int) -> None:
        self.scale_label.setText(S.PAGE_SCALE_VALUE.format(percent=value))
        if not self.scale_slider.isSliderDown():
            self._commit_scale()

    def _commit_scale(self) -> None:
        if self._page is None or self._loading:
            return
        value = self.scale_slider.value() / 100
        current = round(min(max(self._page.scale, SCALE_MIN / 100), 1.0), 2)
        if abs(current - value) > 1e-6:
            self._emit({"scale": value})


if __name__ == "__main__":
    pass
