"""The Combine dialog: put two or more controllers on one page (journey board J12).

Opened from Export › "Combine onto one page…" and Pages › "New page…" (create),
or Pages › "Edit…" (an existing page). Fields: Name, the controllers (only
Ready controllers can be ticked; the others are shown disabled with "needs a
template"), the arrangement (each with its one-line description), the page size
(A4, Letter, Kneeboard 5.5×8.5in, Fit to content, Custom…), the orientation,
the scaling sentence and the scale slider, and "Export them only on this page,
not as separate diagrams". A live thumbnail is composed on a worker
(``render/compose.compose_page`` with the first profile the page is made for)
and drawn with ``QSvgRenderer``. Problems are plain sentences under the fields
(``PageService.validate``); Create stays disabled until there are none.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import (
    QObject,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.render.page import (
    Arrangement,
    Orientation,
    Page,
    Placement,
    ProfileRule,
    SizePreset,
)
from joystick_diagrams.ui import strings_diagrams as S

_logger = logging.getLogger(__name__)

THUMB_SIZE = QSize(360, 260)
THUMB_DEBOUNCE_MS = 250
SCALE_MIN = 25
SCALE_MAX = 100
ERROR_STYLE = "color: #F87171;"
HELP_STYLE = "color: #9AA0A6; font-size: 12px;"
LINK_STYLE = (
    "QPushButton { color: #8AB4F8; background: transparent; border: none; "
    "padding: 0; text-align: left; text-transform: none; font-size: 12px; } "
    "QPushButton:hover { text-decoration: underline; }"
)

ARRANGEMENTS: tuple[tuple[Arrangement, str], ...] = (
    (Arrangement.SIDE_BY_SIDE, S.ARRANGE_SIDE_BY_SIDE),
    (Arrangement.STACKED, S.ARRANGE_STACKED),
    (Arrangement.GRID, S.ARRANGE_GRID),
)
SIZES: tuple[tuple[SizePreset, str], ...] = (
    (SizePreset.A4, "A4"),
    (SizePreset.LETTER, "Letter"),
    (SizePreset.KNEEBOARD, S.SIZE_KNEEBOARD),
    (SizePreset.FIT, "Fit to content"),
    (SizePreset.CUSTOM, S.SIZE_CUSTOM),
)
ORIENTATIONS: tuple[Orientation, ...] = (
    Orientation.AUTO,
    Orientation.PORTRAIT,
    Orientation.LANDSCAPE,
)


def controller_choices(statuses: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """``(guid, name, can_be_ticked)`` for the Controllers list: Ready ones first."""
    from joystick_diagrams.device_status import DeviceStatus

    waiting = (DeviceStatus.NEEDS_TEMPLATE, DeviceStatus.TEMPLATE_MISSING)
    ready = [(g, i.name or g, True) for g, i in statuses.items() if i.state.exports]
    needs = [(g, i.name or g, False) for g, i in statuses.items() if i.state in waiting]
    ready.sort(key=lambda c: c[1].casefold())
    needs.sort(key=lambda c: c[1].casefold())
    return ready + needs


def _number(value: str | None, default: float = 0.0) -> float:
    try:
        return float(str(value).replace("px", "").replace("mm", "").strip())
    except (TypeError, ValueError):
        return default


def flatten_nested_svgs(svg_text: str) -> str:
    """Turn each nested ``<svg x y width height viewBox>`` panel into a transformed
    ``<g>`` (``QSvgRenderer`` implements SVG Tiny and skips nested ``<svg>``)."""
    from lxml import etree

    root = etree.fromstring(svg_text.encode("utf-8"))
    svg_tag = root.tag  # "{http://www.w3.org/2000/svg}svg"
    for nested in list(root.iter(svg_tag)):
        if nested is root:
            continue
        x, y = _number(nested.get("x")), _number(nested.get("y"))
        width = _number(nested.get("width"), 0)
        height = _number(nested.get("height"), 0)
        box = [
            _number(v) for v in (nested.get("viewBox") or "").replace(",", " ").split()
        ]
        transform = f"translate({x:g},{y:g})"
        if len(box) == 4 and box[2] > 0 and box[3] > 0 and width and height:
            scale = min(width / box[2], height / box[3])
            transform += f" scale({scale:g}) translate({-box[0]:g},{-box[1]:g})"
        group = etree.Element(
            etree.QName(svg_tag).namespace
            and f"{{{etree.QName(svg_tag).namespace}}}g"
            or "g"
        )
        group.set("transform", transform)
        if nested.get("opacity"):
            group.set("opacity", nested.get("opacity"))
        for child in list(nested):
            group.append(child)
        parent = nested.getparent()
        parent.replace(nested, group)
    return etree.tostring(root, encoding="unicode")


def render_thumbnail(svg_text: str, size: QSize = THUMB_SIZE) -> QImage:
    """Draw an SVG into an image that fits ``size`` (keeps the aspect ratio)."""
    from PySide6.QtSvg import QSvgRenderer

    try:
        svg_text = flatten_nested_svgs(svg_text)
    except Exception as error:  # noqa: BLE001 - draw what Qt can
        _logger.debug(f"Thumbnail panels not flattened: {error}")
    renderer = QSvgRenderer(svg_text.encode("utf-8"))
    view = renderer.viewBoxF()
    width, height = size.width(), size.height()
    if view.width() > 0 and view.height() > 0:
        ratio = view.width() / view.height()
        if width / height > ratio:
            width = max(int(height * ratio), 1)
        else:
            height = max(int(width / ratio), 1)
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.white)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image


class _ThumbSignals(QObject):
    done = Signal(int, object)  # generation, QImage
    failed = Signal(int, str)


class ThumbnailRunnable(QRunnable):
    def __init__(self, generation: int, page: Page, wrapper: Any, devices: list[Any]):
        super().__init__()
        self.generation = generation
        self.page = page
        self.wrapper = wrapper
        self.devices = devices
        self.signals = _ThumbSignals()

    @Slot()
    def run(self) -> None:
        try:
            from joystick_diagrams.render import build_render_context
            from joystick_diagrams.render.compose import (
                compose_page,
                member_devices_for_profile,
            )

            members = member_devices_for_profile(self.page, self.wrapper, self.devices)
            result = compose_page(
                self.page, self.wrapper, members, build_render_context()
            )
            image = render_thumbnail(result.svg_text)
        except Exception as error:  # noqa: BLE001 - shown as a sentence
            _logger.warning(f"Page thumbnail failed: {error}")
            self.signals.failed.emit(self.generation, str(error))
            return
        self.signals.done.emit(self.generation, image)


def profile_game(wrapper: Any) -> str:
    origin = getattr(wrapper, "profile_origin", None)
    return str(getattr(origin, "name", "") or "")


def profile_line(entry: Any, names: dict[str, str]) -> str:
    """ "DCS World / A-10C_2", or "… — no Warthog Throttle bindings" when a
    controller on the page has none in that profile."""
    wrapper = entry.wrapper
    game = profile_game(wrapper)
    base = (
        S.RULE_LIST_ENTRY.format(game=game, profile=wrapper.profile_name)
        if game
        else wrapper.profile_name
    )
    if not entry.missing:
        return base
    missing = S.join_and([names.get(g, g) for g in entry.missing])
    return S.RULE_LIST_MISSING.format(entry=base, controllers=missing)


class PagesDialog(QDialog):
    """Create (``page=None``) or edit a combined page."""

    def __init__(
        self,
        parent: QWidget | None = None,
        page: Page | None = None,
        *,
        statuses: dict[str, Any] | None = None,
        export_devices: list[Any] | None = None,
        preselect: list[str] | None = None,
        live_preview: bool = True,
    ):
        super().__init__(parent)
        self.appState = AppState()
        self.service = self.appState.page_service
        self._editing = page
        self.page: Page | None = None  # the saved page after accept
        self._statuses = statuses if statuses is not None else self._load_statuses()
        self._devices = (
            export_devices if export_devices is not None else self._load_devices()
        )
        self._live = live_preview
        self._generation = 0
        self._pool = QThreadPool(self)  # its own: never queued behind other work
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(THUMB_DEBOUNCE_MS)
        self._timer.timeout.connect(self.update_thumbnail)
        self._name_edited = page is not None

        self.setWindowTitle(S.COMBINE_EDIT_TITLE if page else S.COMBINE_TITLE)
        self.setMinimumWidth(1000)
        root = QVBoxLayout(self)
        root.setSpacing(12)
        body = QHBoxLayout()
        body.setSpacing(20)
        root.addLayout(body, 1)

        # ── Left: the fields ──
        form = QFormLayout()
        form.setSpacing(10)
        self.name_edit = QLineEdit()
        self.name_edit.setAccessibleName(S.COMBINE_NAME)
        self.name_edit.textEdited.connect(self._on_name_edited)
        form.addRow(S.COMBINE_NAME, self.name_edit)

        members = QVBoxLayout()
        members.setSpacing(4)
        self.member_boxes: dict[str, QCheckBox] = {}
        for guid, name, enabled in controller_choices(self._statuses):
            box = QCheckBox(
                name if enabled else S.COMBINE_NEEDS_TEMPLATE.format(controller=name)
            )
            box.setEnabled(enabled)
            box.toggled.connect(self._changed)
            self.member_boxes[guid] = box
            members.addWidget(box)
        members_widget = QWidget()
        members_widget.setLayout(members)
        form.addRow(S.COMBINE_CONTROLLERS, members_widget)

        # "Make this page for": which profiles get a page, with live counts
        rule_box = QVBoxLayout()
        rule_box.setSpacing(4)
        self.rule_group = QButtonGroup(self)
        self.rule_shared = QRadioButton()
        self.rule_any = QRadioButton()
        for index, radio in enumerate((self.rule_shared, self.rule_any)):
            self.rule_group.addButton(radio, index)
            rule_box.addWidget(radio)
        any_help = QLabel(S.RULE_ANY_HELP)
        any_help.setWordWrap(True)
        any_help.setStyleSheet(HELP_STYLE + " padding-left: 30px;")
        rule_box.addWidget(any_help)
        self.rule_shared.setChecked(True)
        self.rule_group.idToggled.connect(
            lambda _id, checked: checked and self._changed()
        )
        self.rule_list_toggle = QPushButton(S.RULE_SHOW_LIST)
        self.rule_list_toggle.setFlat(True)
        self.rule_list_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rule_list_toggle.setStyleSheet(LINK_STYLE)
        self.rule_list_toggle.clicked.connect(self._toggle_rule_list)
        rule_box.addWidget(self.rule_list_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self.rule_list = QLabel()
        self.rule_list.setWordWrap(True)
        self.rule_list.setStyleSheet(HELP_STYLE)
        self.rule_list.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.rule_list.hide()
        rule_box.addWidget(self.rule_list)
        rule_widget = QWidget()
        rule_widget.setLayout(rule_box)
        make_for = QLabel(S.COMBINE_MAKE_FOR)
        make_for.setWordWrap(True)
        form.addRow(make_for, rule_widget)
        self._plans: dict[ProfileRule, list[Any]] = {}

        arrangement = QVBoxLayout()
        arrangement.setSpacing(4)
        self.arrangement_group = QButtonGroup(self)
        self.arrangement_buttons: dict[Arrangement, QRadioButton] = {}
        for index, (value, text) in enumerate(ARRANGEMENTS):
            radio = QRadioButton(text)
            self.arrangement_group.addButton(radio, index)
            self.arrangement_buttons[value] = radio
            arrangement.addWidget(radio)
        self.arrangement_buttons[Arrangement.SIDE_BY_SIDE].setChecked(True)
        self.arrangement_group.idToggled.connect(
            lambda _id, checked: checked and self._changed()
        )
        arrangement_widget = QWidget()
        arrangement_widget.setLayout(arrangement)
        form.addRow(S.COMBINE_ARRANGEMENT, arrangement_widget)

        size_row = QHBoxLayout()
        self.size_combo = QComboBox()
        self.size_combo.setProperty("class", "view-binds-list")
        self.size_combo.setAccessibleName(S.COMBINE_PAGE_SIZE)
        for value, text in SIZES:
            self.size_combo.addItem(text, value.value)
        self.size_combo.currentIndexChanged.connect(self._on_size_changed)
        size_row.addWidget(self.size_combo)
        self.orientation_combo = QComboBox()
        self.orientation_combo.setProperty("class", "view-binds-list")
        self.orientation_combo.setAccessibleName(S.COMBINE_ORIENTATION)
        for value, text in zip(ORIENTATIONS, S.ORIENTATION_CHOICES, strict=True):
            self.orientation_combo.addItem(text, value.value)
        self.orientation_combo.currentIndexChanged.connect(self._changed)
        size_row.addWidget(QLabel(S.COMBINE_ORIENTATION))
        size_row.addWidget(self.orientation_combo)
        size_row.addStretch(1)
        size_widget = QWidget()
        size_widget.setLayout(size_row)
        form.addRow(S.COMBINE_PAGE_SIZE, size_widget)

        custom_row = QHBoxLayout()
        self.width_spin = QDoubleSpinBox()
        self.height_spin = QDoubleSpinBox()
        for spin, label in (
            (self.width_spin, S.SIZE_CUSTOM_WIDTH),
            (self.height_spin, S.SIZE_CUSTOM_HEIGHT),
        ):
            spin.setRange(0, 2000)
            spin.setDecimals(1)
            spin.setAccessibleName(label)
            spin.valueChanged.connect(self._changed)
            custom_row.addWidget(QLabel(label))
            custom_row.addWidget(spin)
        self.width_spin.setValue(210)
        self.height_spin.setValue(297)
        custom_row.addStretch(1)
        self.custom_widget = QWidget()
        self.custom_widget.setLayout(custom_row)
        self.custom_widget.hide()
        form.addRow("", self.custom_widget)

        scaling = QLabel(S.COMBINE_SCALING)
        scaling.setWordWrap(True)
        scaling.setStyleSheet(HELP_STYLE)
        form.addRow("", scaling)

        scale_row = QHBoxLayout()
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(SCALE_MIN, SCALE_MAX)
        self.scale_slider.setValue(SCALE_MAX)
        self.scale_slider.setAccessibleName(S.COMBINE_SCALE)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        scale_row.addWidget(self.scale_slider, 1)
        self.scale_label = QLabel(S.COMBINE_SCALE_VALUE.format(percent=SCALE_MAX))
        self.scale_label.setMinimumWidth(40)
        scale_row.addWidget(self.scale_label)
        scale_widget = QWidget()
        scale_widget.setLayout(scale_row)
        form.addRow(S.COMBINE_SCALE, scale_widget)

        self.only_on_page = QCheckBox(S.COMBINE_ONLY_ON_PAGE)
        self.only_on_page.setChecked(True)
        form.addRow("", self.only_on_page)
        self.only_on_page_help = QLabel(S.COMBINE_ONLY_ON_PAGE_HELP)
        self.only_on_page_help.setWordWrap(True)
        self.only_on_page_help.setStyleSheet(HELP_STYLE + " padding-left: 30px;")
        form.addRow("", self.only_on_page_help)

        self.problems_label = QLabel()
        self.problems_label.setWordWrap(True)
        self.problems_label.setStyleSheet(ERROR_STYLE)
        form.addRow("", self.problems_label)
        left = QWidget()
        left.setLayout(form)
        body.addWidget(left, 1)

        # ── Right: the thumbnail ──
        right = QVBoxLayout()
        right.setSpacing(8)
        self.thumbnail = QLabel(S.COMBINE_PREVIEW_NONE)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setWordWrap(True)
        self.thumbnail.setFixedSize(THUMB_SIZE)
        self.thumbnail.setStyleSheet(
            "background: #252830; border: 1px solid #3C4043; border-radius: 6px; "
            "color: #9AA0A6;"
        )
        right.addWidget(self.thumbnail)
        self.thumbnail_caption = QLabel()
        self.thumbnail_caption.setStyleSheet(HELP_STYLE)
        right.addWidget(self.thumbnail_caption)
        one_file = QLabel(S.PAGE_ONE_FILE_PER_PROFILE)
        one_file.setWordWrap(True)
        one_file.setStyleSheet(HELP_STYLE)
        right.addWidget(one_file)
        right.addStretch(1)
        right_widget = QWidget()
        right_widget.setLayout(right)
        right_widget.setFixedWidth(THUMB_SIZE.width() + 20)
        body.addWidget(right_widget, 0)

        self.buttons = QDialogButtonBox()
        self.buttons.addButton(S.COMBINE_CANCEL, QDialogButtonBox.ButtonRole.RejectRole)
        self.create_button = self.buttons.addButton(
            S.COMBINE_SAVE if page else S.COMBINE_CREATE,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self._load(page, preselect or [])
        self.name_edit.setFocus()

    # ── Data ──

    @staticmethod
    def _load_statuses() -> dict[str, Any]:
        try:
            from joystick_diagrams.device_status import all_device_statuses

            return all_device_statuses(
                list(AppState().profile_wrappers), include_unseen=False
            )
        except Exception as error:  # noqa: BLE001
            _logger.warning(f"Could not work out controller statuses: {error}")
            return {}

    @staticmethod
    def _load_devices() -> list[Any]:
        try:
            from joystick_diagrams.ui.device_setup_controller import get_export_devices

            return list(get_export_devices())
        except Exception as error:  # noqa: BLE001
            _logger.warning(f"Could not load controllers: {error}")
            return []

    def _load(self, page: Page | None, preselect: list[str]) -> None:
        if page is None:
            self.name_edit.setText(
                S.COMBINE_DEFAULT_NAME.format(number=len(self.service.pages()) + 1)
            )
            for guid in preselect:
                box = self.member_boxes.get(guid)
                if box is not None and box.isEnabled():
                    box.setChecked(True)
            self._changed()
            return
        self.name_edit.setText(page.name)
        for guid in page.member_guids:
            box = self.member_boxes.get(guid)
            if box is not None:
                box.setChecked(True)
        self.arrangement_buttons[page.arrangement].setChecked(True)
        self.size_combo.setCurrentIndex(
            max(self.size_combo.findData(page.size_preset.value), 0)
        )
        self.orientation_combo.setCurrentIndex(
            max(self.orientation_combo.findData(page.orientation.value), 0)
        )
        if page.size_preset is SizePreset.CUSTOM:
            self.width_spin.setValue(page.width_mm or 0)
            self.height_spin.setValue(page.height_mm or 0)
        self.scale_slider.setValue(round(min(max(page.scale, 0.25), 1.0) * 100))
        self.only_on_page.setChecked(not page.export_members_separately)
        (
            self.rule_any if page.profile_rule is ProfileRule.ANY else self.rule_shared
        ).setChecked(True)
        self._changed()

    def member_guids(self) -> list[str]:
        return [g for g, box in self.member_boxes.items() if box.isChecked()]

    def arrangement(self) -> Arrangement:
        for value, radio in self.arrangement_buttons.items():
            if radio.isChecked():
                return value
        return Arrangement.SIDE_BY_SIDE

    def profile_rule(self) -> ProfileRule:
        return ProfileRule.ANY if self.rule_any.isChecked() else ProfileRule.SHARED

    def plan(self, rule: ProfileRule | None = None) -> list[Any]:
        """The profiles the page would be made for under ``rule`` (the chosen one)."""
        return self._plans.get(rule or self.profile_rule(), [])

    def size_preset(self) -> SizePreset:
        return SizePreset(self.size_combo.currentData())

    def build_page(self) -> Page:
        """The page as the fields describe it (not saved)."""
        size = self.size_preset()
        fields = {
            "name": self.name_edit.text(),
            "arrangement": self.arrangement(),
            "size_preset": size,
            "orientation": Orientation(self.orientation_combo.currentData()),
            "width_mm": self.width_spin.value() if size is SizePreset.CUSTOM else None,
            "height_mm": self.height_spin.value()
            if size is SizePreset.CUSTOM
            else None,
            "scale": self.scale_slider.value() / 100,
            "export_members_separately": not self.only_on_page.isChecked(),
            "profile_rule": self.profile_rule(),
        }
        guids = self.member_guids()
        if self._editing is not None:
            existing = {p.device_guid: p for p in self._editing.placements}
            fields["placements"] = [
                existing.get(g, Placement(device_guid=g)) for g in guids
            ]
            return self._editing.model_copy(update=fields)
        return Page(placements=[Placement(device_guid=g) for g in guids], **fields)

    def problems(self) -> list[str]:
        try:
            page = self.build_page()
        except ValueError as error:
            return [str(error)]
        problems = self.service.validate(page)
        if not problems and not self.plan():
            problems.append(
                S.RULE_NONE_SHARED
                if self.profile_rule() is ProfileRule.SHARED
                else S.RULE_NONE_ANY
            )
        return problems

    def _controller_names(self) -> dict[str, str]:
        names = {}
        for guid, box in self.member_boxes.items():
            info = self._statuses.get(guid)
            names[guid] = (
                (getattr(info, "name", None) or box.text()) if info else box.text()
            )
        return names

    def _update_rule_section(self) -> None:
        """Live counts on both choices and the list of resulting profiles."""
        from joystick_diagrams.render.compose import page_profile_plan

        guids = self.member_guids()
        page = Page(name="-", placements=[Placement(device_guid=g) for g in guids])
        self._plans = {
            rule: page_profile_plan(page, self._devices, rule)
            if len(guids) >= 2
            else []
            for rule in ProfileRule
        }
        shared = len(self._plans[ProfileRule.SHARED])
        anyone = len(self._plans[ProfileRule.ANY])
        controllers = (
            S.RULE_BOTH_CONTROLLERS
            if len(guids) == 2
            else S.RULE_ALL_CONTROLLERS.format(count=max(len(guids), 2))
        )
        self.rule_shared.setText(
            S.RULE_SHARED.format(
                controllers=controllers, profiles=S.counted(shared, S.PROFILES)
            )
        )
        self.rule_any.setText(S.RULE_ANY.format(profiles=S.counted(anyone, S.PROFILES)))
        names = self._controller_names()
        lines = [profile_line(entry, names) for entry in self.plan()]
        self.rule_list.setText("\n".join(lines))
        self.rule_list_toggle.setVisible(bool(lines))
        if not lines:
            self.rule_list.hide()

    def _toggle_rule_list(self) -> None:
        showing = not self.rule_list.isVisible()
        self.rule_list.setVisible(showing)
        self.rule_list_toggle.setText(S.RULE_HIDE_LIST if showing else S.RULE_SHOW_LIST)

    # ── Reactions ──

    def _on_name_edited(self, _text: str) -> None:
        self._name_edited = True
        self._changed()

    def _on_size_changed(self, _index: int) -> None:
        custom = self.size_preset() is SizePreset.CUSTOM
        self.custom_widget.setVisible(custom)
        fit = self.size_preset() is SizePreset.FIT
        self.orientation_combo.setEnabled(not fit)
        self._changed()

    def _on_scale_changed(self, value: int) -> None:
        self.scale_label.setText(S.COMBINE_SCALE_VALUE.format(percent=value))
        self._changed()

    def _changed(self, *_args) -> None:
        if not hasattr(self, "create_button"):
            return  # still building the dialog
        if not self._name_edited and self._editing is None:
            names = [self.member_boxes[g].text() for g in self.member_guids()[:3]]
            if len(names) >= 2:
                self.name_edit.setText(" + ".join(names))
        self._update_rule_section()
        problems = self.problems()
        self.problems_label.setText(" ".join(problems))
        self.problems_label.setVisible(bool(problems))
        self.create_button.setEnabled(not problems)
        if self._live:
            self._timer.start()

    def preview_profile(self, page: Page | None = None) -> Any:
        from joystick_diagrams.export import page_profiles

        page = page or self.build_page()
        if len(page.member_guids) < 2:
            return None
        try:
            from joystick_diagrams.render.compose import profiles_for_page

            # The first profile every controller is bound in, when there is one
            profiles = profiles_for_page(
                page, self._devices, ProfileRule.SHARED
            ) or page_profiles(page, self._devices)
        except Exception:  # noqa: BLE001
            return None
        return profiles[0] if profiles else None

    def update_thumbnail(self) -> None:
        self._generation += 1
        try:
            page = self.build_page()
        except ValueError:
            page = None
        wrapper = self.preview_profile(page) if page is not None else None
        if page is None or wrapper is None:
            self.thumbnail.setPixmap(QPixmap())
            self.thumbnail.setText(S.COMBINE_PREVIEW_NONE)
            self.thumbnail_caption.clear()
            return
        self.thumbnail.setText(S.PAGE_PREVIEW_UPDATING)
        self.thumbnail_caption.setText(
            S.COMBINE_PREVIEW_WITH.format(profile=wrapper.profile_name)
        )
        runnable = ThumbnailRunnable(
            self._generation, page, wrapper, list(self._devices)
        )
        runnable.signals.done.connect(self._on_thumbnail)
        runnable.signals.failed.connect(self._on_thumbnail_failed)
        self._pool.start(runnable)

    def _on_thumbnail(self, generation: int, image: QImage) -> None:
        if generation != self._generation:
            return
        self.thumbnail.setText("")
        self.thumbnail.setPixmap(QPixmap.fromImage(image))

    def _on_thumbnail_failed(self, generation: int, _message: str) -> None:
        if generation != self._generation:
            return
        self.thumbnail.setPixmap(QPixmap())
        self.thumbnail.setText(S.COMBINE_PREVIEW_FAILED)

    # ── Accept ──

    def accept(self) -> None:
        problems = self.problems()
        if problems:
            self.problems_label.setText(" ".join(problems))
            self.problems_label.show()
            return
        try:
            self.page = self.service.save(self.build_page())
        except ValueError as error:
            self.problems_label.setText(str(error))
            self.problems_label.show()
            return
        self._generation += 1
        super().accept()

    def reject(self) -> None:
        self._generation += 1
        super().reject()


if __name__ == "__main__":
    pass
