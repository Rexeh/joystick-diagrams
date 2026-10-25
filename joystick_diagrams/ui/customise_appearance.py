"""Customise → Appearance: the Style tab and the Modifier keys tab (plan §5.5.3/§5.5.4).

Hand-built QWidgets following the other Customise screens. ``refresh()`` is
called on every sidebar switch and must stay cheap: it reloads lists and
toggles, and only re-renders the preview when something changed.

Style tab: a gallery of style cards (Original (unchanged) first), the "Showing
modifiers" choice, a compact editor and a live preview rendered through the
real pipeline. Editing a built-in silently creates "My style (based on X)".

Modifier keys tab: the "Colour by modifier key" switch, the left/right toggle,
key-name display, the group table (order, colour, keys found in profiles) and
the "Other labels" list. Never says "alias" or "canonical".
"""

import dataclasses
import logging
from collections.abc import Callable

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.input.modifier import ModifierKind
from joystick_diagrams.modifier_identity import (
    DEVICE_INPUT_CANONICAL,
    ModifierDisplay,
    ModifierKeyDisplay,
    ModifierKeyInfo,
    ModifierKeyStyle,
    canonical_of,
    contrast_ratio,
    get_modifier_display,
    get_modifier_key_display,
    modifier_colouring_enabled,
    modifier_sides_merged,
    set_modifier_colouring_enabled,
    set_modifier_display,
    set_modifier_key_display,
    set_modifier_sides_merged,
)
from joystick_diagrams.render import (
    Capability,
    Engine,
    RenderContext,
    RenderNotice,
    RenderOutcome,
    build_render_context,
    resolve_theme,
)
from joystick_diagrams.render.theme import (
    FONT_CHOICES,
    TEMPLATE_ORIGINAL_THEME_ID,
    BoxStyle,
    RoleStyle,
    TextStyle,
    Theme,
    ThemeRole,
    theme_display_name,
)
from joystick_diagrams.ui import strings_appearance as S
from joystick_diagrams.ui.appearance_preview import AppearancePreview
from joystick_diagrams.ui.widgets.colour_button import ColourButton
from joystick_diagrams.ui.widgets.empty_state import EmptyState
from joystick_diagrams.ui.widgets.surface_card import SurfaceCard

_logger = logging.getLogger(__name__)

TEXT_ROLES = (ThemeRole.BOUND, ThemeRole.UNBOUND, ThemeRole.MODIFIER)
ALL_ROLES = tuple(ThemeRole)
UNBOUND_FADED = {"text": "#9CA3AF", "stroke": "#D1D5DB"}
UNBOUND_FILL = "#F3F4F6"
# Labels carry their own stylesheet, which makes Qt paint the inherited widget
# background behind them as a darker band; keep them transparent.
HELP_STYLE = "color: #9AA0A6; font-size: 12px; background: transparent;"
HEADING_STYLE = (
    "color: #E8EAED; font-size: 14px; font-weight: bold; background: transparent;"
)
WARNING_STYLE = "color: #F59E0B; font-size: 11px; background: transparent;"
CHIP_STYLE = "color: #E8EAED; font-size: 12px; padding: 2px; background: transparent;"
CARD_OBJECT_NAME = "style_card"
CARD_SELECTED_STYLE = (
    f"QFrame#{CARD_OBJECT_NAME} {{ border: 2px solid #4C8BF5; border-radius: 6px; }}"
)
TEXT_CONTRAST_MINIMUM = 4.5  # WCAG AA, normal text
STROKE_CONTRAST_MINIMUM = 3.0  # WCAG non-text contrast (box strokes)
ICON_COLOUR = "#E8EAED"
ICON_COLOUR_DISABLED = "#5F6368"
ORDER_BUTTON_SIZE = QSize(28, 24)
# qt-material styles QToolButton as a 36px bar with 12px side borders, which
# squeezes an icon-only button into a sliver; these buttons set their own look.
ORDER_BUTTON_STYLE = """
QToolButton {
    background: #2c2f38; border: 1px solid #3C4043; border-radius: 4px;
    margin: 0px; padding: 2px; min-width: 28px; min-height: 24px;
}
QToolButton:hover { background: #3C4043; border-color: #5F6368; }
QToolButton:pressed { background: #4C8BF5; border-color: #4C8BF5; }
QToolButton:disabled { background: transparent; border-color: #2c2f38; }
"""


def _help(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(HELP_STYLE)
    return label


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(HEADING_STYLE)
    return label


def _open_export_page() -> None:
    main_window = AppState().main_window
    if main_window is not None:
        main_window.load_export_page()


# ── Style tab ──


class StyleCard(QFrame):
    clicked = Signal(str)

    def __init__(self, theme_id: str, title: str, blurb: str, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self.setObjectName(CARD_OBJECT_NAME)
        self.setProperty("class", "surface-card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "surface-card-title")
        row.addWidget(self.title_label, 1)
        self.badge = QLabel(S.CARD_IN_USE)
        self.badge.setProperty("class", "modifier-pill")
        self.badge.setStyleSheet(
            "color: #4C8BF5; font-size: 11px; font-weight: bold; "
            "border: 1px solid #4C8BF5; border-radius: 8px; padding: 1px 8px;"
        )
        self.badge.hide()
        row.addWidget(self.badge)
        layout.addLayout(row)
        layout.addWidget(_help(blurb))

    def set_selected(self, selected: bool) -> None:
        self.setStyleSheet(CARD_SELECTED_STYLE if selected else "")

    def set_in_use(self, in_use: bool) -> None:
        self.badge.setVisible(in_use)

    def mousePressEvent(self, event):  # noqa: N802
        self.clicked.emit(self.theme_id)
        super().mousePressEvent(event)


class StyleTab(QWidget):
    settings_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self.themes = self.appState.theme_service
        self._selected_id = self.themes.active_theme_id()
        self._loading = False
        self._cards: dict[str, StyleCard] = {}
        self._export_devices: list = []

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setFixedWidth(430)
        left = QWidget()
        self._left = QVBoxLayout(left)
        self._left.setContentsMargins(0, 0, 8, 0)
        self._left.setSpacing(16)
        self._build_gallery()
        self._build_showing_modifiers()
        self._build_editor()
        self._left.addStretch(1)
        self._scroll.setWidget(left)
        root.addWidget(self._scroll)

        root.addWidget(self._build_preview_column(), 1)

        self.refresh()

    # ── Construction ──

    def _build_gallery(self) -> None:
        self._left.addWidget(_heading(S.STYLE_GALLERY_HEADING))
        self._left.addWidget(_help(S.STYLE_GALLERY_HELP))
        self._gallery = QVBoxLayout()
        self._gallery.setSpacing(8)
        self._left.addLayout(self._gallery)

    def _build_showing_modifiers(self) -> None:
        card = SurfaceCard(S.SHOWING_MODIFIERS_HEADING)
        card.content_layout.addWidget(_help(S.SHOWING_MODIFIERS_HELP))
        self._display_group = QButtonGroup(self)
        self._display_buttons: dict[ModifierDisplay, QRadioButton] = {}
        for display, text, help_text in (
            (
                ModifierDisplay.TEMPLATE_BOXES,
                S.SHOWING_TEMPLATE_BOXES,
                S.SHOWING_TEMPLATE_BOXES_HELP,
            ),
            (
                ModifierDisplay.UNDER_MAIN_TEXT,
                S.SHOWING_UNDER_MAIN_TEXT,
                S.SHOWING_UNDER_MAIN_TEXT_HELP,
            ),
            (
                ModifierDisplay.MERGED_SAME_LINE,
                S.SHOWING_MERGED_SAME_LINE,
                S.SHOWING_MERGED_SAME_LINE_HELP,
            ),
        ):
            radio = QRadioButton(text)
            radio.setToolTip(help_text)
            self._display_group.addButton(radio)
            self._display_buttons[display] = radio
            card.content_layout.addWidget(radio)
            hint = _help(help_text)
            hint.setContentsMargins(24, 0, 0, 4)
            card.content_layout.addWidget(hint)
            radio.toggled.connect(
                lambda checked, d=display: checked and self._on_display_changed(d)
            )
        self._left.addWidget(card)

    def _build_editor(self) -> None:
        self._editor_card = SurfaceCard(S.EDITOR_HEADING)
        self._editor_hint = _help(S.EDITOR_ORIGINAL_HINT)
        self._editor_card.content_layout.addWidget(self._editor_hint)
        self._editor_form_widget = QWidget()
        form = QFormLayout(self._editor_form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.font_combo = QComboBox()
        self.font_combo.setProperty("class", "view-binds-list")
        self._populate_fonts()
        self.font_combo.currentIndexChanged.connect(lambda _i: self._on_font_changed())
        form.addRow(S.FIELD_FONT, self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 48)
        self.size_spin.setSpecialValueText(S.FIELD_FONT_SIZE_TEMPLATE)
        self.size_spin.setSuffix(" px")
        self.size_spin.valueChanged.connect(
            lambda v: self._edit(lambda t: self._set_size(t, v))
        )
        form.addRow(S.FIELD_FONT_SIZE, self.size_spin)

        self.text_colour = ColourButton(allow_none=True)
        self.text_colour.colour_changed.connect(
            lambda c: self._edit(lambda t: self._set_text_colour(t, c))
        )
        form.addRow(S.FIELD_TEXT_COLOUR, self.text_colour)

        self.box_colour = ColourButton(allow_none=True)
        self.box_colour.colour_changed.connect(
            lambda c: self._edit(lambda t: self._set_box_stroke(t, c))
        )
        form.addRow(S.FIELD_BOX_COLOUR, self.box_colour)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(-1, 24)
        self.radius_spin.setSpecialValueText(
            S.FIELD_FONT_TEMPLATE.replace("font", "corners")
        )
        self.radius_spin.setSuffix(" px")
        self.radius_spin.valueChanged.connect(
            lambda v: self._edit(lambda t: self._set_radius(t, v))
        )
        form.addRow(S.FIELD_BOX_RADIUS, self.radius_spin)

        self.unbound_combo = QComboBox()
        self.unbound_combo.setProperty("class", "view-binds-list")
        for text in (S.UNBOUND_TEMPLATE, S.UNBOUND_FADED, S.UNBOUND_LIGHT_FILL):
            self.unbound_combo.addItem(text)
        self.unbound_combo.currentIndexChanged.connect(
            lambda i: self._edit(lambda t: self._set_unbound(t, i))
        )
        form.addRow(S.FIELD_UNBOUND, self.unbound_combo)

        self.leader_colour = ColourButton(allow_none=True)
        self.leader_colour.colour_changed.connect(
            lambda c: self._edit(lambda t: setattr(t.leader_line, "stroke", c))
        )
        form.addRow(S.FIELD_LEADER_COLOUR, self.leader_colour)

        self.leader_width = QDoubleSpinBox()
        self.leader_width.setRange(0, 10)
        self.leader_width.setSingleStep(0.5)
        self.leader_width.setSpecialValueText(
            S.FIELD_FONT_TEMPLATE.replace("font", "width")
        )
        self.leader_width.setSuffix(" px")
        self.leader_width.valueChanged.connect(
            lambda v: self._edit(
                lambda t: setattr(t.leader_line, "stroke_width", v or None)
            )
        )
        form.addRow(S.FIELD_LEADER_WIDTH, self.leader_width)

        self._editor_card.content_layout.addWidget(self._editor_form_widget)
        self._editor_card.content_layout.addWidget(_help(S.FONT_GAP_NOTE))

        buttons = QHBoxLayout()
        self.reset_button = QPushButton()
        self.reset_button.setProperty("class", "plugin-setup-button")
        self.reset_button.setIcon(qta.icon("fa5s.undo", color="white"))
        self.reset_button.clicked.connect(self._on_reset)
        buttons.addWidget(self.reset_button)
        self.delete_button = QPushButton(S.BUTTON_DELETE_STYLE)
        self.delete_button.setProperty("class", "plugin-setup-button")
        self.delete_button.setIcon(qta.icon("fa5s.trash", color="white"))
        self.delete_button.clicked.connect(self._on_delete)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        self._editor_card.content_layout.addLayout(buttons)
        self._left.addWidget(self._editor_card)

    def _build_preview_column(self) -> QWidget:
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(_heading(S.PREVIEW_HEADING))
        self.preview_combo = QComboBox()
        self.preview_combo.setProperty("class", "view-binds-list")
        self.preview_combo.setMinimumWidth(260)
        self.preview_combo.currentIndexChanged.connect(
            lambda _i: self._on_preview_source_changed()
        )
        header.addWidget(self.preview_combo, 1)
        self.use_button = QPushButton(S.BUTTON_USE_FOR_EXPORTS)
        self.use_button.setProperty("class", "run-button")
        self.use_button.setIcon(qta.icon("fa5s.check", color="white"))
        self.use_button.clicked.connect(self._on_use_for_exports)
        header.addWidget(self.use_button)
        layout.addLayout(header)

        self.preview = AppearancePreview()
        self.preview.render_started.connect(
            lambda: self.status_label.setText(S.PREVIEW_RENDERING)
        )
        self.preview.render_finished.connect(self._on_preview_rendered)
        self.empty_state = EmptyState(
            S.PREVIEW_EMPTY, "fa5s.file-code", S.PREVIEW_EMPTY_ACTION
        )
        self.empty_state.action_requested.connect(_open_export_page)
        self.empty_state.hide()
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.empty_state, 1)

        self.status_label = _help("")
        layout.addWidget(self.status_label)
        return column

    def _populate_fonts(self) -> None:
        installed = set(QFontDatabase.families())
        self.font_combo.addItem(S.FIELD_FONT_TEMPLATE, None)
        for choice in FONT_CHOICES:
            if choice.ofl and choice.family not in installed:
                continue
            self.font_combo.addItem(choice.family, choice.family)

    # ── Refresh ──

    def refresh(self) -> None:
        if self.themes.get(self._selected_id) is None:
            self._selected_id = TEMPLATE_ORIGINAL_THEME_ID
        self._rebuild_gallery()
        self._load_display()
        self._load_editor()
        self._reload_preview_sources()
        self.preview.refresh()

    def _rebuild_gallery(self) -> None:
        while self._gallery.count():
            item = self._gallery.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._cards = {}
        entries = [
            (TEMPLATE_ORIGINAL_THEME_ID, S.ORIGINAL_CARD_TITLE, S.ORIGINAL_CARD_BLURB)
        ]
        for theme in self.themes.builtin_themes():
            entries.append(
                (theme.theme_id, theme.name, S.BUILTIN_BLURBS.get(theme.theme_id, ""))
            )
        for theme in self.themes.user_themes():
            base = theme_display_name(theme.based_on)
            blurb = (
                S.CARD_BASED_ON.format(base=base)
                if theme.based_on
                else S.USER_STYLE_BLURB
            )
            entries.append((theme.theme_id, theme.name, blurb))
        active = self.themes.active_theme_id()
        for theme_id, title, blurb in entries:
            card = StyleCard(theme_id, title, blurb)
            card.clicked.connect(self._on_card_clicked)
            card.set_selected(theme_id == self._selected_id)
            card.set_in_use(theme_id == active)
            self._cards[theme_id] = card
            self._gallery.addWidget(card)
        self.use_button.setEnabled(self._selected_id != active)
        self.use_button.setText(
            S.BUTTON_IN_USE if self._selected_id == active else S.BUTTON_USE_FOR_EXPORTS
        )

    def _load_display(self) -> None:
        self._loading = True
        try:
            self._display_buttons[get_modifier_display()].setChecked(True)
        finally:
            self._loading = False

    def _load_editor(self) -> None:
        theme = self.themes.get(self._selected_id)
        self._editor_form_widget.setEnabled(theme is not None)
        self.reset_button.setVisible(theme is not None)
        self.delete_button.setVisible(
            theme is not None and not self.themes.is_builtin(theme.theme_id)
        )
        if theme is None:
            self._editor_hint.setText(S.EDITOR_ORIGINAL_HINT)
            return
        base = theme_display_name(theme.based_on) if theme.based_on else theme.name
        self.reset_button.setText(S.BUTTON_RESET_TO.format(base=base))
        self.reset_button.setEnabled(bool(theme.based_on))
        self._editor_hint.setText(
            S.EDITOR_COPY_NOTE if self.themes.is_builtin(theme.theme_id) else ""
        )
        self._loading = True
        try:
            self._load_editor_values(theme)
        finally:
            self._loading = False

    def _load_editor_values(self, theme: Theme) -> None:
        bound = theme.role(ThemeRole.BOUND)
        family = bound.text.font_family
        index = self.font_combo.findData(family)
        if index < 0 and family:
            self.font_combo.addItem(family, family)
            index = self.font_combo.count() - 1
        self.font_combo.setCurrentIndex(max(index, 0))
        self.size_spin.setValue(int(bound.text.font_size or 0))
        self.text_colour.set_colour(bound.text.colour)
        self.box_colour.set_colour(bound.box.stroke)
        radius = bound.box.corner_radius
        self.radius_spin.setValue(-1 if radius is None else int(radius))
        unbound = theme.role(ThemeRole.UNBOUND).box
        self.unbound_combo.setCurrentIndex(
            2 if unbound.fill else 1 if unbound.stroke else 0
        )
        self.leader_colour.set_colour(theme.leader_line.stroke)
        self.leader_width.setValue(theme.leader_line.stroke_width or 0)

    def _reload_preview_sources(self) -> None:
        from joystick_diagrams.ui.device_setup_controller import get_export_devices

        try:
            devices = [ed for ed in get_export_devices() if ed.has_template]
        except Exception as e:  # noqa: BLE001 - never let the screen fail to open
            _logger.warning(f"Could not load devices for the preview: {e}")
            devices = []
        signature = [
            (
                ed.device_id,
                ed.profile_wrapper.profile_key,
                str(ed.template.template_path),
            )
            for ed in devices
        ]
        if signature == getattr(self, "_source_signature", None):
            return
        self._source_signature = signature
        self._export_devices = devices
        self.preview_combo.blockSignals(True)
        self.preview_combo.clear()
        for ed in devices:
            self.preview_combo.addItem(
                S.PREVIEW_DEVICE_PROFILE.format(
                    device=ed.device_name, profile=ed.profile_wrapper.profile_name
                )
            )
        self.preview_combo.blockSignals(False)
        has_devices = bool(devices)
        self.preview_combo.setVisible(has_devices)
        self.preview.setVisible(has_devices)
        self.empty_state.setVisible(not has_devices)
        self._on_preview_source_changed()

    # ── Preview ──

    def _preview_context(self) -> RenderContext:
        ctx = build_render_context()
        return dataclasses.replace(
            ctx, theme=resolve_theme(self.themes.get(self._selected_id))
        )

    def _on_preview_source_changed(self) -> None:
        index = self.preview_combo.currentIndex()
        if 0 <= index < len(self._export_devices):
            self.preview.set_source(self._export_devices[index], self._preview_context)
        else:
            self.preview.set_source(None, self._preview_context)

    def mark_preview_dirty(self) -> None:
        self.preview.mark_dirty()

    def _on_preview_rendered(self, outcome: RenderOutcome) -> None:
        report = outcome.report
        if RenderNotice.FELL_BACK_TO_LEGACY in report.notices:
            text = S.PREVIEW_FELL_BACK
        elif (
            report.engine is Engine.LEGACY
            or self._selected_id == TEMPLATE_ORIGINAL_THEME_ID
        ):
            text = S.PREVIEW_ORIGINAL
        elif Capability.SHAPE_STYLE not in report.capabilities:
            text = S.PREVIEW_LIMITED
        else:
            text = S.PREVIEW_STYLED.format(
                style=theme_display_name(self._selected_id, self.themes.all_themes())
            )
        if report.overflow:
            text += " " + S.PREVIEW_OVERFLOW.format(count=len(report.overflow))
        self.status_label.setText(text)

    # ── Handlers ──

    def _on_card_clicked(self, theme_id: str) -> None:
        if theme_id == self._selected_id:
            return
        self._selected_id = theme_id
        for card_id, card in self._cards.items():
            card.set_selected(card_id == theme_id)
        active = self.themes.active_theme_id()
        self.use_button.setEnabled(theme_id != active)
        self.use_button.setText(
            S.BUTTON_IN_USE if theme_id == active else S.BUTTON_USE_FOR_EXPORTS
        )
        self._load_editor()
        self.mark_preview_dirty()

    def _on_use_for_exports(self) -> None:
        self.themes.set_active(self._selected_id)
        self._rebuild_gallery()
        self.settings_changed.emit()

    def _on_display_changed(self, display: ModifierDisplay) -> None:
        if self._loading:
            return
        set_modifier_display(display)
        self.mark_preview_dirty()
        self.settings_changed.emit()

    def _edit(self, mutate: Callable[[Theme], None]) -> None:
        """Apply an editor change to the selected style, copying a built-in first."""
        if self._loading:
            return
        theme = self.themes.get(self._selected_id)
        if theme is None:
            return
        copied = False
        if self.themes.is_builtin(theme.theme_id):
            theme = self.themes.ensure_editable(theme.theme_id)
            self._selected_id = theme.theme_id
            copied = True
        edited = theme.model_copy(deep=True)
        mutate(edited)
        try:
            self.themes.save(edited)
        except ValueError as e:
            _logger.warning(f"Could not save style: {e}")
            return
        if copied:
            self._rebuild_gallery()
            self._load_editor()
        self.mark_preview_dirty()
        self.settings_changed.emit()

    def _on_font_changed(self) -> None:
        family = self.font_combo.currentData()
        self._edit(lambda t: self._set_font(t, family))

    def _on_reset(self) -> None:
        theme = self.themes.get(self._selected_id)
        if theme is None or not theme.based_on:
            return
        self.themes.reset_to_base(theme.theme_id)
        self._load_editor()
        self.mark_preview_dirty()
        self.settings_changed.emit()

    def _on_delete(self) -> None:
        theme = self.themes.get(self._selected_id)
        if theme is None or self.themes.is_builtin(theme.theme_id):
            return
        self.themes.delete(theme.theme_id)
        self._selected_id = theme.based_on or TEMPLATE_ORIGINAL_THEME_ID
        self.refresh()
        self.mark_preview_dirty()
        self.settings_changed.emit()

    # ── Theme mutators (static so they are easy to test) ──

    @staticmethod
    def _role(theme: Theme, role: ThemeRole) -> RoleStyle:
        return theme.roles.setdefault(role, RoleStyle())

    @classmethod
    def _set_font(cls, theme: Theme, family: str | None) -> None:
        for role in ALL_ROLES:
            cls._role(theme, role).text.font_family = family

    @classmethod
    def _set_size(cls, theme: Theme, size: int) -> None:
        for role in TEXT_ROLES:
            cls._role(theme, role).text.font_size = size or None

    @classmethod
    def _set_text_colour(cls, theme: Theme, colour: str | None) -> None:
        cls._role(theme, ThemeRole.BOUND).text.colour = colour

    @classmethod
    def _set_box_stroke(cls, theme: Theme, colour: str | None) -> None:
        cls._role(theme, ThemeRole.BOUND).box.stroke = colour
        cls._role(theme, ThemeRole.MODIFIER).box.stroke = colour

    @classmethod
    def _set_radius(cls, theme: Theme, radius: int) -> None:
        for role in TEXT_ROLES:
            cls._role(theme, role).box.corner_radius = None if radius < 0 else radius

    @classmethod
    def _set_unbound(cls, theme: Theme, option: int) -> None:
        if option == 0:
            theme.roles[ThemeRole.UNBOUND] = RoleStyle()
            return
        role = cls._role(theme, ThemeRole.UNBOUND)
        role.text = TextStyle(
            colour=UNBOUND_FADED["text"],
            font_family=role.text.font_family,
            font_size=role.text.font_size,
        )
        role.box = BoxStyle(
            stroke=UNBOUND_FADED["stroke"],
            stroke_width=1,
            fill=UNBOUND_FILL if option == 2 else None,
            corner_radius=role.box.corner_radius,
        )


# ── Modifier keys tab ──


class ModifierKeysTab(QWidget):
    settings_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self.keys = self.appState.modifier_key_service
        self._loading = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.master_switch = QCheckBox(S.COLOUR_BY_KEY_HEADING)
        self.master_switch.setStyleSheet(HEADING_STYLE)
        self.master_switch.toggled.connect(self._on_master_toggled)
        layout.addWidget(self.master_switch)
        layout.addWidget(_help(S.COLOUR_BY_KEY_HELP))

        self.sides_switch = QCheckBox(S.SIDES_SAME)
        self.sides_switch.setToolTip(S.SIDES_SAME_HELP)
        self.sides_switch.toggled.connect(self._on_sides_toggled)
        layout.addWidget(self.sides_switch)

        names_row = QHBoxLayout()
        names_row.addWidget(QLabel(S.KEY_NAMES_HEADING))
        self._names_group = QButtonGroup(self)
        self.names_original = QRadioButton(S.KEY_NAMES_ORIGINAL)
        self.names_simplified = QRadioButton(S.KEY_NAMES_SIMPLIFIED)
        for radio in (self.names_original, self.names_simplified):
            self._names_group.addButton(radio)
            names_row.addWidget(radio)
        names_row.addStretch(1)
        self.names_simplified.toggled.connect(self._on_names_toggled)
        layout.addLayout(names_row)

        groups_card = SurfaceCard(S.GROUPS_HEADING)
        groups_card.content_layout.addWidget(_help(S.PRIORITY_HELP))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [S.COLUMN_ORDER, S.COLUMN_COLOUR, S.COLUMN_GROUP, S.COLUMN_KEYS]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setProperty("class", "view-binds-tree")
        self.table.setMinimumHeight(260)
        groups_card.content_layout.addWidget(self.table)
        layout.addWidget(groups_card)

        self.ungrouped_card = SurfaceCard(S.UNGROUPED_HEADING)
        self.ungrouped_card.content_layout.addWidget(_help(S.UNGROUPED_HELP))
        self.ungrouped_label = QLabel()
        self.ungrouped_label.setWordWrap(True)
        self.ungrouped_card.content_layout.addWidget(self.ungrouped_label)
        layout.addWidget(self.ungrouped_card)

        other_card = SurfaceCard(S.OTHER_LABELS_HEADING)
        other_card.content_layout.addWidget(_help(S.OTHER_LABELS_HELP))
        self.other_label = QLabel()
        self.other_label.setWordWrap(True)
        other_card.content_layout.addWidget(self.other_label)
        layout.addWidget(other_card)

        buttons = QHBoxLayout()
        self.restore_button = QPushButton(S.BUTTON_RESTORE_DEFAULTS)
        self.restore_button.setProperty("class", "plugin-setup-button")
        self.restore_button.setIcon(qta.icon("fa5s.undo", color="white"))
        self.restore_button.clicked.connect(self._on_restore_defaults)
        buttons.addWidget(self.restore_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addStretch(1)

        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.refresh()

    # ── Refresh ──

    def refresh(self) -> None:
        self._loading = True
        try:
            self.master_switch.setChecked(modifier_colouring_enabled())
            self.sides_switch.setChecked(modifier_sides_merged())
            simplified = get_modifier_key_display() is ModifierKeyDisplay.SIMPLIFIED
            (self.names_simplified if simplified else self.names_original).setChecked(
                True
            )
        finally:
            self._loading = False
        self._rebuild_table()

    def _discovered(self):
        snapshot = self.keys.snapshot()
        grouped: dict[str, list] = {}
        ungrouped: list = []
        qualifiers: list = []
        for found in self.keys.discover(self.appState.profile_wrappers):
            if found.kind is ModifierKind.QUALIFIER:
                qualifiers.append(found)
                continue
            kind, canonical = canonical_of(found.raw, snapshot, found.kind)
            if snapshot.group(kind, canonical) is not None:
                grouped.setdefault(canonical, []).append(found)
            else:
                ungrouped.append(found)
        return grouped, ungrouped, qualifiers

    @staticmethod
    def _chip(found) -> str:
        plugins = ", ".join(sorted(found.plugins)) or "your profiles"
        return S.KEY_CHIP.format(
            key=found.raw,
            plugin=plugins,
            count=found.count,
            s="" if found.count == 1 else "s",
        )

    def _rebuild_table(self) -> None:
        grouped, ungrouped, qualifiers = self._discovered()
        groups = [g for g in self.keys.get_groups() if g.kind is ModifierKind.KEY]
        self.table.setRowCount(len(groups))
        for row, info in enumerate(groups):
            self.table.setCellWidget(row, 0, self._order_widget(info, row, len(groups)))
            self.table.setCellWidget(row, 1, self._colour_widget(info))
            name = QTableWidgetItem(info.display_label or info.canonical)
            if info.canonical == DEVICE_INPUT_CANONICAL:
                name.setToolTip(S.DEVICE_BUTTONS_HINT)
            self.table.setItem(row, 2, name)
            chips = [self._chip(f) for f in grouped.get(info.canonical, [])]
            text = "\n".join(chips) if chips else S.NO_KEYS_SEEN
            if info.canonical == DEVICE_INPUT_CANONICAL:
                text += f"\n{S.DEVICE_BUTTONS_HINT}"
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(HELP_STYLE if not chips else CHIP_STYLE)
            self.table.setCellWidget(row, 3, label)
        self.table.resizeRowsToContents()
        self.ungrouped_label.setText(
            "\n".join(self._chip(f) for f in ungrouped) or S.OTHER_LABELS_NONE
        )
        self.ungrouped_card.setVisible(bool(ungrouped))
        self.other_label.setText(
            "\n".join(self._chip(f) for f in qualifiers) or S.OTHER_LABELS_NONE
        )

    @staticmethod
    def _order_button(icon: str, label: str, enabled: bool) -> QToolButton:
        """An icon-only move button: ``label`` is its accessible name and tooltip."""
        button = QToolButton()
        button.setIcon(
            qta.icon(icon, color=ICON_COLOUR, color_disabled=ICON_COLOUR_DISABLED)
        )
        button.setIconSize(QSize(14, 14))
        button.setFixedSize(ORDER_BUTTON_SIZE)
        button.setStyleSheet(ORDER_BUTTON_STYLE)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(label)
        button.setToolTip(label)
        button.setEnabled(enabled)
        return button

    def _order_widget(self, info: ModifierKeyInfo, row: int, count: int) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name = info.display_label or info.canonical
        up = self._order_button(
            "fa5s.chevron-up", S.MOVE_UP_NAMED.format(name=name), row > 0
        )
        up.clicked.connect(lambda: self._move(info, -1))
        down = self._order_button(
            "fa5s.chevron-down", S.MOVE_DOWN_NAMED.format(name=name), row < count - 1
        )
        down.clicked.connect(lambda: self._move(info, 1))
        layout.addWidget(up)
        layout.addWidget(down)
        return widget

    def _colour_widget(self, info: ModifierKeyInfo) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)
        button = ColourButton(info.style.colour if info.style else None)
        warning = QLabel()
        warning.setStyleSheet(WARNING_STYLE)
        warning.setWordWrap(True)
        self._update_warning(warning, info.style)
        button.colour_changed.connect(
            lambda c, i=info, w=warning: self._on_colour_changed(i, c, w)
        )
        layout.addWidget(button)
        layout.addWidget(warning)
        return widget

    @staticmethod
    def _update_warning(label: QLabel, style: ModifierKeyStyle | None) -> None:
        """Warn when the printed text (darkened shade) or the box stroke is hard to see."""
        if style is None:
            label.setVisible(False)
            return
        text_ratio = contrast_ratio(style.resolved_text_colour, "#FFFFFF")
        stroke_ratio = contrast_ratio(style.colour, "#FFFFFF")
        failing = (
            stroke_ratio
            if stroke_ratio < STROKE_CONTRAST_MINIMUM
            else text_ratio
            if text_ratio < TEXT_CONTRAST_MINIMUM
            else None
        )
        label.setText(S.LOW_CONTRAST.format(ratio=failing) if failing else "")
        label.setVisible(failing is not None)

    # ── Handlers ──

    def _emit(self) -> None:
        if not self._loading:
            self.settings_changed.emit()

    def _on_master_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        set_modifier_colouring_enabled(checked)
        self._emit()

    def _on_sides_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        set_modifier_sides_merged(checked)
        self._rebuild_table()
        self._emit()

    def _on_names_toggled(self, simplified: bool) -> None:
        if self._loading:
            return
        set_modifier_key_display(
            ModifierKeyDisplay.SIMPLIFIED if simplified else ModifierKeyDisplay.ORIGINAL
        )
        self._emit()

    def _on_colour_changed(
        self, info: ModifierKeyInfo, colour: str | None, warning: QLabel
    ) -> None:
        if colour is None:
            return
        style = ModifierKeyStyle(colour=colour)
        self.keys.set_style(info.kind, info.canonical, style)
        self._update_warning(warning, style)
        self._emit()

    def _move(self, info: ModifierKeyInfo, direction: int) -> None:
        groups = [g for g in self.keys.get_groups() if g.kind is ModifierKind.KEY]
        index = next(
            (i for i, g in enumerate(groups) if g.canonical == info.canonical), None
        )
        if index is None:
            return
        other_index = index + direction
        if not 0 <= other_index < len(groups):
            return
        other = groups[other_index]
        mine, theirs = info.priority, other.priority
        if mine == theirs:
            theirs = mine - direction
        self.keys.set_priority(info.kind, info.canonical, theirs)
        self.keys.set_priority(other.kind, other.canonical, mine)
        self._rebuild_table()
        self._emit()

    def _on_restore_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            S.BUTTON_RESTORE_DEFAULTS,
            S.RESTORE_DEFAULTS_CONFIRM,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.keys.restore_defaults()
        self.refresh()
        self._emit()


# ── Page ──


class CustomiseAppearance(QWidget):
    """Customise → Appearance with the Style and Modifier keys tabs."""

    TAB_STYLE = 0
    TAB_MODIFIER_KEYS = 1

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.setProperty("class", "configure-tabwidget")
        self.style_tab = StyleTab()
        self.modifier_keys_tab = ModifierKeysTab()
        self.tabs.addTab(self.style_tab, S.TAB_STYLE)
        self.tabs.addTab(self.modifier_keys_tab, S.TAB_MODIFIER_KEYS)
        layout.addWidget(self.tabs)
        self.modifier_keys_tab.settings_changed.connect(
            self.style_tab.mark_preview_dirty
        )
        self.tabs.currentChanged.connect(lambda _i: self.refresh())

    def refresh(self) -> None:
        """Cheap: reloads lists and toggles; the preview only re-renders when dirty."""
        current = self.tabs.currentWidget()
        if current is not None and hasattr(current, "refresh"):
            current.refresh()

    def show_tab(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)
