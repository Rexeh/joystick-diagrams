"""Stage 1, Setup (boards J01–J03, J14): which games are read and from where.

- **First launch** (no game added): "Which games do you play?" from the hosted
  game list (the existing catalogue fetch, parsers only, compatible ones), each
  game a card that toggles its checkbox; "Don't see your game? Add a game from a
  file…"; the footer primary is "Add DCS World and continue ›". Offline: the
  plain notice with [Try again] and the file route.
- **Game cards**: name · folder, "Verified"/"Community" chip, a status line
  ("12 profiles · read 09:41"), "Read this game", [Settings…] [Choose folder…]
  [Read again] and Remove. A game that needs its folder shows the folder card:
  candidates from the optional ``PluginInterface.suggested_paths()`` hook
  ("Found <path> · Last changed 24 Oct" [Use this folder and read it], "Also
  found…" [Use this one instead]) and "Not the right place? Choose folder…"; a
  folder is never used until the player has seen it here. A read that found no
  bindings turns the card amber; a failed read says what failed and what is kept.
- **Results card** after a read: "We found 6 controllers in 12 profiles", who
  needs a template, who is set to No diagram and why (``device_status`` reasons),
  and the template definition.

Reading itself belongs to the shell (``MainWindow.start_read``): this page asks
through ``read_requested`` (``None`` = every ready game, or a list of wrappers)
and follows ``on_read_started`` / ``on_read_finished``. ``populate_plugin_cards``
keeps its name because ``plugin_install_flow`` calls it after an install.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db import db_settings
from joystick_diagrams.ui import strings_controllers as SC
from joystick_diagrams.ui import strings_setup as S
from joystick_diagrams.ui.stage_contract import (
    PAYLOAD_DEVICE_GUID,
    STAGE_CONTROLLERS,
    NextAction,
    ReadOutcome,
    StageStatus,
)
from joystick_diagrams.ui.widgets.confirm import show_problem

_logger = logging.getLogger(__name__)

PLUGIN_UPDATES_DISMISSED_KEY = "plugin_updates_dismissed"
PLUGIN_CATALOG_LAST_CHECKED_KEY = "plugin_catalog_last_checked"
CATALOG_VERIFIED_KEY = "catalog_verified_games"  # {game name: signed} from the list

COLOUR_OK = "#34D399"
COLOUR_WARNING = "#F59E0B"
COLOUR_ERROR = "#F87171"
COLOUR_BUSY = "#4C8BF5"
COLOUR_MUTED = "#9AA0A6"

PAGE_QSS = """
QPushButton, QToolButton { text-transform: none; }
QCheckBox { background: transparent; }
QLabel { background: transparent; }
QLabel#setupTitle { color: #E8EAED; font-size: 18px; font-weight: 700; }
QLabel#setupSubtitle, QLabel#muted { color: #9AA0A6; font-size: 12px; }
QLabel#cardName { color: #E8EAED; font-size: 13px; font-weight: 700; }
QLabel#cardFolder { color: #9AA0A6; font-size: 12px; }
QLabel#cardStatus { color: #9AA0A6; font-size: 11px; }
QLabel#cardStatus[state="ok"] { color: #34D399; }
QLabel#cardStatus[state="warning"] { color: #F59E0B; }
QLabel#cardStatus[state="error"] { color: #F87171; }
QLabel#chip { color: #34D399; background: rgba(52,211,153,0.12); border-radius: 3px;
    padding: 1px 6px; font-size: 10px; font-weight: 700; }
QLabel#chip[tone="community"] { color: #F59E0B; background: rgba(245,158,11,0.12); }
QLabel#willBeAdded { color: #8AB4F8; font-size: 11px; font-weight: 700; }
QLabel#blockTitle { color: #E8EAED; font-size: 13px; font-weight: 700; }
QLabel#candidatePath { color: #E8EAED; font-size: 12px; font-family: monospace; }
QLabel#resultsTitle { color: #E8EAED; font-size: 14px; font-weight: 700; }
QLabel#bigCount { color: #E8EAED; font-size: 20px; font-weight: 700; }
QLabel#bigCount[tone="warning"] { color: #F59E0B; }
QLabel#bigCount[tone="ok"] { color: #34D399; }
QLabel#problem { color: #F87171; font-size: 12px; }
QFrame#gameCard, QFrame#resultsCard, QFrame#pickerCard, QFrame#settingsPanel {
    background: #252830; border: 1px solid #3C4043; border-radius: 8px;
}
QFrame#gameCard[state="ok"] { border-left: 3px solid #34D399; }
QFrame#gameCard[state="warning"] { border-left: 3px solid #F59E0B; }
QFrame#gameCard[state="error"] { border-left: 3px solid #F87171; }
QFrame#gameCard[state="busy"] { border-left: 3px solid #4C8BF5; }
QFrame#pickerCard:hover { border-color: #4C8BF5; }
QFrame#pickerCard[checked="true"] { border-color: #2F6FDB; background: rgba(47,111,219,0.10); }
QFrame#folderBlock, QFrame#noticeBlock {
    background: #1f2229; border: 1px solid #3C4043; border-radius: 6px;
}
QFrame#noticeBlock[tone="warning"] { border-color: rgba(245,158,11,0.45); }
QPushButton#setupAction {
    background: #2c2f38; color: #E8EAED; border: 1px solid #7A808A; border-radius: 4px;
    min-height: 30px; padding: 0px 14px; font-size: 11px; font-weight: 700;
}
QPushButton#setupAction:hover { border-color: #4C8BF5; }
QPushButton#setupAction:focus { border: 2px solid #4C8BF5; }
QPushButton#setupAction:disabled { color: #6B7280; border-color: #3C4043; }
QPushButton#setupPrimary {
    background: #2F6FDB; color: #ffffff; border: 1px solid #2F6FDB; border-radius: 4px;
    min-height: 30px; padding: 0px 14px; font-size: 11px; font-weight: 700;
}
QPushButton#setupPrimary:hover { background: #4C8BF5; border-color: #4C8BF5; }
QPushButton#setupPrimary:focus { border: 2px solid #8AB4F8; }
QToolButton#cardRemove { background: transparent; border: none; border-radius: 4px; padding: 4px; }
QToolButton#cardRemove:hover { background: #3C4043; }
QPushButton#setupLink {
    background: transparent; border: none; color: #8AB4F8; padding: 2px 0px;
    text-align: left; font-size: 12px; font-weight: 700;
}
QPushButton#setupLink:hover { text-decoration: underline; }
"""


# ── Game helpers ──


def _is_path_field(field_info: Any) -> bool:
    annotation = field_info.annotation
    return annotation is Path or (
        hasattr(annotation, "__args__") and Path in annotation.__args__
    )


def path_fields(wrapper: Any) -> list[tuple[str, Any]]:
    settings = getattr(wrapper, "plugin_settings", None)
    if settings is None:
        return []
    return [
        (name, info)
        for name, info in type(settings).model_fields.items()
        if _is_path_field(info)
    ]


def other_fields(wrapper: Any) -> list[tuple[str, Any]]:
    settings = getattr(wrapper, "plugin_settings", None)
    if settings is None:
        return []
    return [
        (name, info)
        for name, info in type(settings).model_fields.items()
        if not _is_path_field(info)
    ]


def primary_path_field(wrapper: Any) -> tuple[str, Any] | None:
    fields = path_fields(wrapper)
    return fields[0] if fields else None


def wants_file(wrapper: Any) -> bool:
    field = primary_path_field(wrapper)
    if field is None:
        return False
    extra = field[1].json_schema_extra or {}
    return not extra.get("is_folder", True)


def current_path(wrapper: Any) -> Path | None:
    field = primary_path_field(wrapper)
    if field is None:
        return None
    value = getattr(wrapper.plugin_settings, field[0], None)
    return Path(value) if value else None


def suggested_paths(wrapper: Any) -> list[Path]:
    """Existing candidates from the game's optional ``suggested_paths()`` hook."""
    plugin = getattr(wrapper, "plugin", None)
    hook = getattr(plugin, "suggested_paths", None)
    if not callable(hook):
        return []
    try:
        candidates = list(hook() or [])
    except Exception as error:  # noqa: BLE001 - a hook must never break Setup
        _logger.warning(f"suggested_paths() failed for {wrapper.name}: {error}")
        return []
    seen: list[Path] = []
    for candidate in candidates:
        try:
            path = Path(candidate).expanduser()
        except TypeError:
            continue
        if path.exists() and path not in seen:
            seen.append(path)
    return seen


def short_date(moment: datetime) -> str:
    if moment.year == datetime.now().year:
        return f"{moment.day} {moment.strftime('%b')}"
    return f"{moment.day} {moment.strftime('%b')} {moment.year}"


def candidate_facts(path: Path) -> str:
    """ "Last changed 24 Oct" when the folder can be looked at cheaply."""
    try:
        moment = datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return ""
    return S.FOLDER_LAST_CHANGED.format(date=short_date(moment))


def catalog_verified_flags() -> dict[str, bool]:
    """The game list's Verified flag per game name, as last fetched."""
    try:
        raw = db_settings.get_setting(CATALOG_VERIFIED_KEY)
        flags = json.loads(raw) if raw else {}
    except Exception:  # noqa: BLE001 - a courtesy, never a failure
        return {}
    return (
        {str(k): bool(v) for k, v in flags.items()} if isinstance(flags, dict) else {}
    )


def remember_catalog_flags(catalog: Any) -> bool:
    """Store the Verified flag of every game on the list; True when it changed."""
    flags = {
        entry.name: bool(entry.signed)
        for entry in getattr(catalog, "plugins", []) or []
        if getattr(entry, "type", "parser") == "parser"
    }
    if not flags or flags == catalog_verified_flags():
        return False
    try:
        db_settings.add_update_setting_value(CATALOG_VERIFIED_KEY, json.dumps(flags))
    except Exception as error:  # noqa: BLE001
        _logger.debug(f"Could not remember the game list flags: {error}")
        return False
    return True


def is_verified(wrapper: Any) -> bool | None:
    """True for Verified, False for Community, None when nothing is known.

    A copy whose signature checked out when it was added is Verified. Otherwise the
    game list decides: a game listed as Verified there shows Verified (however it
    was added, such as from a local folder); one listed as Community, or one the
    player trusted by hand, shows Community.
    """
    try:
        from joystick_diagrams.db.db_plugin_trust import get_trust_reason

        reason = get_trust_reason(wrapper.name, "parser")
    except Exception:  # noqa: BLE001
        reason = None
    if reason == "signature_valid":
        return True
    listed = catalog_verified_flags().get(wrapper.name)
    if listed is not None:
        return listed
    if reason is None:
        return None
    return False


def apply_path(wrapper: Any, field_name: str, path: Path) -> str | None:
    """Store a folder or file on the game; the plain problem text when it can't."""
    try:
        wrapper.update_setting(field_name, path)
    except Exception as error:  # noqa: BLE001 - the plugin says why in its own words
        try:
            wrapper.update_setting(field_name, None)
        except Exception:  # noqa: BLE001
            pass
        wrapper.push_error(str(error))
        return str(error) or type(error).__name__
    wrapper.push_error("")
    return None


def ask_for_path(
    parent: QWidget,
    wrapper: Any,
    field: tuple[str, Any] | None = None,
    title: str | None = None,
) -> Path | None:
    """Ask for a game's folder (or file). ``title`` replaces the "Where does …
    keep your bindings?" dialog title (other apps keep other things there)."""
    field = field or primary_path_field(wrapper)
    if field is None:
        return None
    _name, info = field
    extra = info.json_schema_extra or {}
    start = current_path(wrapper) or Path(extra.get("default_path", "~")).expanduser()
    if extra.get("is_folder", True):
        result = QFileDialog.getExistingDirectory(
            parent, title or S.FOLDER_DIALOG_TITLE.format(game=wrapper.name), str(start)
        )
        return Path(result) if result else None
    extensions = extra.get("extensions", []) or []
    patterns = " ".join(f"*{e}" for e in extensions) if extensions else "*"
    result, _ = QFileDialog.getOpenFileName(
        parent,
        title or S.FILE_DIALOG_TITLE.format(game=wrapper.name),
        str(start),
        S.FILE_DIALOG_FILTER.format(patterns=patterns),
    )
    return Path(result) if result else None


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


def _button(
    text: str, handler: Callable[[], None], primary: bool = False
) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("setupPrimary" if primary else "setupAction")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(lambda _checked=False: handler())
    return button


def _label(text: str, name: str = "muted", wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


def _restyle(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# ── First-launch picker ──


class PickerCard(QFrame):
    """One game in "Which games do you play?"; the whole card toggles the box."""

    toggled = Signal()

    def __init__(self, entry: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("pickerCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        self.checkbox = QCheckBox()
        self.checkbox.setAccessibleName(entry.name)
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox)
        column = QVBoxLayout()
        column.setSpacing(2)
        column.addWidget(_label(entry.name, "cardName", wrap=False))
        detail = S.PICKER_VERIFIED if entry.signed else S.PICKER_COMMUNITY
        if getattr(entry, "description", ""):
            detail = f"{detail} · {entry.description}"
        column.addWidget(_label(detail))
        layout.addLayout(column, 1)
        self.will_be_added = _label(S.PICKER_WILL_BE_ADDED, "willBeAdded", wrap=False)
        self.will_be_added.hide()
        layout.addWidget(self.will_be_added)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
        super().mousePressEvent(event)

    def _on_toggled(self, checked: bool) -> None:
        self.setProperty("checked", "true" if checked else "false")
        self.will_be_added.setVisible(checked)
        _restyle(self)
        self.toggled.emit()

    @property
    def checked(self) -> bool:
        return self.checkbox.isChecked()


class GamePicker(QWidget):
    """Loading / offline / list states of "Which games do you play?"."""

    selection_changed = Signal()
    retry_requested = Signal()
    add_from_file_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.cards: list[PickerCard] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        root.addLayout(self.body)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(_label(S.PICKER_DONT_SEE, wrap=False))
        self.add_from_file = QPushButton(S.PICKER_ADD_FROM_FILE)
        self.add_from_file.setObjectName("setupLink")
        self.add_from_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_from_file.clicked.connect(self.add_from_file_requested.emit)
        row.addWidget(self.add_from_file)
        row.addStretch(1)
        root.addLayout(row)
        self.set_loading()

    def set_loading(self) -> None:
        self._reset()
        self.body.addWidget(_label(S.PICKER_LOADING))

    def set_unavailable(self, text: str = S.PICKER_OFFLINE) -> None:
        self._reset()
        self.body.addWidget(_label(text))
        retry = _button(S.PICKER_TRY_AGAIN, self.retry_requested.emit)
        self.body.addWidget(retry, 0, Qt.AlignmentFlag.AlignLeft)

    def set_entries(self, entries: list[Any]) -> None:
        if not entries:
            self.set_unavailable(S.PICKER_EMPTY)
            return
        self._reset()
        for entry in entries:
            card = PickerCard(entry)
            card.toggled.connect(self.selection_changed.emit)
            self.cards.append(card)
            self.body.addWidget(card)

    def selected_entries(self) -> list[Any]:
        return [card.entry for card in self.cards if card.checked]

    def _reset(self) -> None:
        self.cards = []
        _clear_layout(self.body)
        self.selection_changed.emit()


# ── Game card ──


class GameCard(QFrame):
    """One added game: what it reads, how it went, what to do next."""

    def __init__(self, page: SetupPage, wrapper: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.page = page
        self.wrapper = wrapper
        self.setObjectName("gameCard")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(QIcon(wrapper.icon).pixmap(QSize(32, 32)))
        icon.setFixedSize(32, 32)
        head.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        column = QVBoxLayout()
        column.setSpacing(3)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        self.name_label = _label(wrapper.name, "cardName", wrap=False)
        name_row.addWidget(self.name_label)
        self.folder_label = _label("", "cardFolder", wrap=False)
        self.folder_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        name_row.addWidget(self.folder_label, 1)
        verified = is_verified(wrapper)
        if verified is not None:
            chip = _label(
                S.CARD_VERIFIED if verified else S.CARD_COMMUNITY, "chip", wrap=False
            )
            chip.setProperty("tone", "verified" if verified else "community")
            chip.setToolTip(S.CARD_VERIFIED_TIP if verified else S.CARD_COMMUNITY_TIP)
            name_row.addWidget(chip)
        column.addLayout(name_row)
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(12, 12)
        status_row.addWidget(self.status_icon)
        self.status_label = _label("", "cardStatus", wrap=False)
        status_row.addWidget(self.status_label, 1)
        column.addLayout(status_row)
        head.addLayout(column, 1)

        self.read_this = QCheckBox(S.CARD_READ_THIS_GAME)
        self.read_this.setToolTip(S.CARD_READ_THIS_GAME_TIP)
        self.read_this.setChecked(bool(wrapper.enabled))
        self.read_this.toggled.connect(
            lambda on: QTimer.singleShot(0, lambda: page.set_game_enabled(wrapper, on))
        )
        head.addWidget(self.read_this, 0, Qt.AlignmentFlag.AlignTop)
        self.settings_button = _button(
            S.CARD_SETTINGS, lambda: page.show_settings(wrapper)
        )
        head.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignTop)
        self.folder_button = _button(
            S.CARD_CHOOSE_FILE if wants_file(wrapper) else S.CARD_CHOOSE_FOLDER,
            lambda: page.choose_folder(wrapper),
        )
        head.addWidget(self.folder_button, 0, Qt.AlignmentFlag.AlignTop)
        self.read_button = _button(
            S.CARD_READ_AGAIN, lambda: page.read_games([wrapper])
        )
        head.addWidget(self.read_button, 0, Qt.AlignmentFlag.AlignTop)
        self.remove_button = QToolButton()
        self.remove_button.setIcon(qta.icon("fa5s.trash-alt", color=COLOUR_MUTED))
        self.remove_button.setToolTip(S.CARD_REMOVE_TIP.format(game=wrapper.name))
        self.remove_button.setAccessibleName(
            S.CARD_REMOVE_TIP.format(game=wrapper.name)
        )
        self.remove_button.setAutoRaise(True)
        self.remove_button.setObjectName("cardRemove")
        self.remove_button.clicked.connect(lambda: page.remove_game(wrapper))
        self.remove_button.setVisible(page.is_removable(wrapper))
        head.addWidget(self.remove_button, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        root.addLayout(self.body)

    def set_state(self, state: str, text: str) -> None:
        self.setProperty("state", state)
        self.status_label.setProperty("state", state)
        self.status_label.setText(text)
        icon = {
            "ok": ("fa5s.check-circle", COLOUR_OK),
            "warning": ("fa5s.exclamation-triangle", COLOUR_WARNING),
            "error": ("fa5s.times-circle", COLOUR_ERROR),
            "busy": ("fa5s.sync", COLOUR_BUSY),
        }.get(state)
        if icon is None:
            self.status_icon.clear()
            self.status_icon.hide()
        else:
            self.status_icon.setPixmap(
                qta.icon(icon[0], color=icon[1]).pixmap(QSize(12, 12))
            )
            self.status_icon.show()
        _restyle(self)
        _restyle(self.status_label)

    def clear_body(self) -> None:
        _clear_layout(self.body)


# ── Settings panel ──


class GameSettingsPanel(QFrame):
    """Every setting a game has: its folders first, then its options."""

    changed = Signal()
    close_requested = Signal()

    def __init__(
        self, wrapper: Any, parent: QWidget | None = None, for_app: bool = False
    ):
        super().__init__(parent)
        self.wrapper = wrapper
        self._for_app = for_app  # an other app (Settings › Other apps), not a game
        self.setObjectName("settingsPanel")
        self.setFixedWidth(340)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 14, 14)
        layout.setSpacing(8)
        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QIcon(wrapper.icon).pixmap(QSize(24, 24)))
        head.addWidget(icon)
        head.addWidget(_label(wrapper.name, "cardName", wrap=False), 1)
        close = QToolButton()
        close.setIcon(qta.icon("fa5s.times", color=COLOUR_MUTED))
        close.setToolTip(S.PANEL_CLOSE)
        close.setAccessibleName(S.PANEL_CLOSE)
        close.setAutoRaise(True)
        close.clicked.connect(self.close_requested.emit)
        head.addWidget(close)
        layout.addLayout(head)
        layout.addWidget(_label(S.PANEL_VERSION.format(version=wrapper.version)))

        self.problem = _label("", "problem")
        self.problem.hide()
        fields = path_fields(wrapper)
        if fields:
            layout.addWidget(
                _label(
                    S.PANEL_FOLDER if len(fields) == 1 else S.PANEL_FOLDERS,
                    "blockTitle",
                )
            )
            for name, info in fields:
                if len(fields) > 1 or info.title:
                    caption = _label(info.title or name.replace("_", " ").capitalize())
                    caption.setToolTip(info.description or "")
                    layout.addWidget(caption)
                row = QHBoxLayout()
                value = getattr(wrapper.plugin_settings, name, None)
                edit = QLineEdit(str(value) if value else "")
                edit.setReadOnly(True)
                edit.setPlaceholderText(S.PANEL_NOT_CHOSEN)
                row.addWidget(edit, 1)
                row.addWidget(
                    _button(
                        S.PANEL_BROWSE,
                        lambda n=name, i=info, e=edit: self._browse(n, i, e),
                    )
                )
                layout.addLayout(row)
        layout.addWidget(self.problem)
        options = other_fields(wrapper)
        if options:
            layout.addWidget(_label(S.PANEL_SETTINGS, "blockTitle"))
            for name, info in options:
                widget = self._setting_widget(name, info)
                if widget is None:
                    continue
                row = QHBoxLayout()
                caption = _label(info.title or name.replace("_", " ").capitalize())
                caption.setToolTip(info.description or "")
                row.addWidget(caption, 1)
                row.addWidget(widget)
                layout.addLayout(row)
        layout.addStretch(1)

    def _browse(self, name: str, info: Any, edit: QLineEdit) -> None:
        title = (info.title or S.PANEL_FOLDER) if self._for_app else None
        path = ask_for_path(self, self.wrapper, (name, info), title=title)
        if path is None:
            return
        problem = apply_path(self.wrapper, name, path)
        if problem:
            edit.clear()
            self.problem.setText(
                S.PANEL_PATH_PROBLEM.format(game=self.wrapper.name, detail=problem)
            )
            self.problem.show()
        else:
            edit.setText(str(path))
            self.problem.hide()
        self.changed.emit()

    def _setting_widget(self, name: str, info: Any) -> QWidget | None:
        value = getattr(self.wrapper.plugin_settings, name, None)
        if info.annotation is bool:
            box = QCheckBox()
            box.setChecked(bool(value))
            box.setAccessibleName(info.title or name)
            box.toggled.connect(lambda on, n=name: self._set(n, bool(on)))
            return box
        if info.annotation is str:
            options = (info.json_schema_extra or {}).get("options")
            if options:
                combo = QComboBox()
                combo.addItems([str(o) for o in options])
                index = combo.findText(str(value or ""))
                if index >= 0:
                    combo.setCurrentIndex(index)
                combo.currentTextChanged.connect(
                    lambda text, n=name: self._set(n, text)
                )
                return combo
            edit = QLineEdit(str(value or ""))
            edit.editingFinished.connect(lambda n=name, e=edit: self._set(n, e.text()))
            return edit
        return None

    def _set(self, name: str, value: Any) -> None:
        self.wrapper.update_setting(name, value)
        self.changed.emit()


# ── The page ──


class SetupPage(QWidget):
    request_stage = Signal(int, dict)
    state_changed = Signal()
    read_requested = Signal(object)  # None (every ready game) or list[PluginWrapper]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self.setStyleSheet(PAGE_QSS)
        self._pool = QThreadPool.globalInstance()
        self._catalog_worker = None
        self._update_worker = None
        self._catalog_requested = False
        self._reading: list[str] = []
        self._read_times: dict[str, str] = {}
        self._profile_counts: dict[str, int] = {}
        self._failed: dict[str, str] = {}
        self._last_outcome: ReadOutcome | None = None
        self._folder_problems: dict[str, str] = {}
        self._update_count = 0
        self._update_signature: str | None = None
        self._settings_for: str | None = None
        self.cards: dict[str, GameCard] = {}
        self._build_ui()
        self.populate_plugin_cards()

    # ── Construction ──

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(20, 16, 20, 16)
        self.content_layout.setSpacing(12)
        self.title_label = _label("", "setupTitle")
        self.content_layout.addWidget(self.title_label)
        self.subtitle_label = _label("", "setupSubtitle")
        self.content_layout.addWidget(self.subtitle_label)
        self.update_notice = QFrame()
        self.update_notice.setObjectName("noticeBlock")
        notice = QHBoxLayout(self.update_notice)
        notice.setContentsMargins(12, 8, 8, 8)
        self.update_label = _label("")
        notice.addWidget(self.update_label, 1)
        notice.addWidget(_button(S.GAME_UPDATES_SEE, self.open_game_list))
        dismiss = QToolButton()
        dismiss.setIcon(qta.icon("fa5s.times", color=COLOUR_MUTED))
        dismiss.setAutoRaise(True)
        dismiss.setToolTip(S.PANEL_CLOSE)
        dismiss.clicked.connect(self._dismiss_updates)
        notice.addWidget(dismiss)
        self.update_notice.hide()
        self.content_layout.addWidget(self.update_notice)

        self.picker = GamePicker()
        self.picker.selection_changed.connect(self.state_changed.emit)
        self.picker.retry_requested.connect(self.fetch_catalog)
        self.picker.add_from_file_requested.connect(self.add_game_from_file)
        self.content_layout.addWidget(self.picker)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(8)
        self.content_layout.addLayout(self.cards_layout)
        self.add_another = QPushButton(S.ADD_ANOTHER_GAME)
        self.add_another.setObjectName("setupLink")
        self.add_another.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_another.clicked.connect(self.open_game_list)
        self.content_layout.addWidget(self.add_another, 0, Qt.AlignmentFlag.AlignLeft)

        self.results_card = QFrame()
        self.results_card.setObjectName("resultsCard")
        self.results_layout = QVBoxLayout(self.results_card)
        self.results_layout.setContentsMargins(16, 14, 16, 14)
        self.results_layout.setSpacing(8)
        self.results_card.hide()
        self.content_layout.addWidget(self.results_card)
        self.content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self.side_panel = QVBoxLayout()
        self.side_panel.setContentsMargins(0, 16, 16, 16)
        outer.addLayout(self.side_panel)

    # ── Data ──

    @property
    def wrappers(self) -> list[Any]:
        manager = getattr(self.appState, "plugin_manager", None)
        return list(getattr(manager, "plugin_wrappers", None) or [])

    def is_removable(self, wrapper: Any) -> bool:
        manager = getattr(self.appState, "plugin_manager", None)
        getter = getattr(manager, "get_user_plugin_path", None)
        try:
            return bool(callable(getter) and getter(wrapper.name))
        except Exception:  # noqa: BLE001
            return False

    def games_needing_folder(self) -> list[Any]:
        return [w for w in self.wrappers if w.enabled and not w.ready]

    def _profile_count(self, wrapper: Any) -> int | None:
        if wrapper.name in self._profile_counts:
            return self._profile_counts[wrapper.name]
        collection = getattr(wrapper, "plugin_profile_collection", None)
        return len(collection) if collection is not None else None

    def summary(self):
        from joystick_diagrams.ui.controllers_page import compute_statuses

        return compute_statuses(relink=False)

    # ── Contract ──

    def refresh(self) -> None:
        self.populate_plugin_cards()

    def populate_plugin_cards(self) -> None:
        """Redraw everything (kept name: ``plugin_install_flow`` calls it)."""
        wrappers = self.wrappers
        first_launch = not wrappers
        self.picker.setVisible(first_launch)
        self.add_another.setVisible(not first_launch)
        if first_launch:
            self.title_label.setText(S.FIRST_LAUNCH_TITLE)
            self.subtitle_label.setText(S.FIRST_LAUNCH_SUBTITLE)
            if not self._catalog_requested:
                self.fetch_catalog()
        else:
            needing = self.games_needing_folder()
            if needing:
                self.title_label.setText(S.FOLDER_TITLE.format(game=needing[0].name))
            else:
                self.title_label.setText(S.GAMES_TITLE)
            self.subtitle_label.setText(S.GAMES_SUBTITLE)
        self._rebuild_cards()
        self._rebuild_results()
        if self._settings_for is not None:
            wrapper = next((w for w in wrappers if w.name == self._settings_for), None)
            if wrapper is None:
                self.close_settings()
        self.state_changed.emit()

    def stage_status(self) -> StageStatus:
        wrappers = self.wrappers
        if not wrappers:
            return StageStatus("none", S.STATUS_CHOOSE_GAMES)
        if self._reading:
            text = (
                S.STATUS_READING.format(game=self._reading[0])
                if len(self._reading) == 1
                else S.STATUS_READING_MANY
            )
            return StageStatus("busy", text)
        if self._failed:
            return StageStatus(
                "warning", S.STATUS_FAILED.format(game=next(iter(self._failed)))
            )
        needing = self.games_needing_folder()
        if needing:
            if len(needing) == 1:
                return StageStatus(
                    "warning", S.STATUS_NEEDS_FOLDER.format(game=needing[0].name)
                )
            return StageStatus(
                "warning", S.STATUS_NEED_FOLDERS.format(count=len(needing))
            )
        empty = [
            w.name
            for w in wrappers
            if w.enabled and w.name in self._read_times and self._profile_count(w) == 0
        ]
        if empty:
            return StageStatus("warning", S.STATUS_NO_BINDINGS.format(game=empty[0]))
        if self._last_outcome is not None:
            time = self._last_outcome.finished_at
            new = len(self._last_outcome.arrived_guids)
            if new:
                return StageStatus(
                    "ok",
                    S.STATUS_UP_TO_DATE_NEW.format(
                        time=time, count=new, controllers=S.plural(new, S.CONTROLLERS)
                    ),
                )
            return StageStatus("ok", S.STATUS_UP_TO_DATE.format(time=time))
        return StageStatus("none", S.STATUS_READY_TO_READ)

    def next_action(self) -> NextAction | None:
        if not self.wrappers:
            entries = self.picker.selected_entries()
            if not entries:
                return NextAction(S.ADD_NONE, lambda: None, enabled=False)
            label = (
                S.ADD_ONE_AND_CONTINUE.format(game=entries[0].name)
                if len(entries) == 1
                else S.ADD_MANY_AND_CONTINUE.format(count=len(entries))
            )
            return NextAction(
                label, lambda: self.add_games(self.picker.selected_entries())
            )
        summary = self.summary()
        if summary.is_empty:
            # Nothing read yet: the folder card carries the action while a game
            # needs its folder; otherwise reading is the next step.
            if self.games_needing_folder() or self._reading:
                return None
            ready = [w for w in self.wrappers if w.enabled and w.ready]
            if ready:
                label = (
                    S.NEXT_READ_ONE.format(game=ready[0].name)
                    if len(ready) == 1
                    else S.NEXT_READ_MANY.format(count=len(ready))
                )
                return NextAction(label, lambda: self.read_games(None))
        needs = summary.needs
        if needs and not summary.snapshot:
            return NextAction(
                S.NEXT_CHOOSE_TEMPLATES.format(
                    count=len(needs), templates=S.plural(len(needs), S.TEMPLATES)
                ),
                lambda g=needs[0]: self.request_stage.emit(
                    STAGE_CONTROLLERS, {PAYLOAD_DEVICE_GUID: g}
                ),
            )
        return NextAction(
            S.NEXT_CONTROLLERS, lambda: self.request_stage.emit(STAGE_CONTROLLERS, {})
        )

    def footer_hint(self) -> str | None:
        if not self.wrappers:
            return S.FOOTER_HINT_FIRST_LAUNCH
        if self._reading:
            return S.FOOTER_HINT_READING
        if self.games_needing_folder():
            return S.FOOTER_HINT_FOLDERS
        return None

    def handle_request(self, payload: dict) -> None:
        game = payload.get("game")
        wrapper = next((w for w in self.wrappers if w.name == game), None)
        if wrapper is not None and payload.get("action") == "choose_folder":
            self.choose_folder(wrapper)

    navigate = handle_request

    def on_read_started(self, games: list[str]) -> None:
        self._reading = list(games)
        for game in games:
            self._failed.pop(game, None)
        self.populate_plugin_cards()

    def on_read_finished(self, outcome: ReadOutcome) -> None:
        self._reading = []
        self._last_outcome = outcome
        for game in outcome.games:
            if game in outcome.failed:
                self._failed[game] = outcome.failed[game]
            else:
                self._failed.pop(game, None)
                self._read_times[game] = outcome.finished_at
                self._profile_counts[game] = outcome.profiles_per_game.get(game, 0)
        self.populate_plugin_cards()

    @property
    def is_reading(self) -> bool:
        return bool(self._reading)

    # ── Cards ──

    def _rebuild_cards(self) -> None:
        _clear_layout(self.cards_layout)
        self.cards = {}
        asked = False
        for wrapper in self.wrappers:
            card = GameCard(self, wrapper)
            self.cards[wrapper.name] = card
            self.cards_layout.addWidget(card)
            asked = self._fill_card(card, wrapper, asked)

    def _fill_card(self, card: GameCard, wrapper: Any, folder_asked: bool) -> bool:
        path = current_path(wrapper)
        card.folder_label.setText(f"· {path}" if path else "")
        card.folder_label.setToolTip(str(path) if path else "")
        name = wrapper.name
        reading = name in self._reading
        card.read_button.setEnabled(
            bool(wrapper.enabled and wrapper.ready and not reading)
        )
        card.read_button.setVisible(bool(wrapper.ready))
        card.folder_button.setVisible(primary_path_field(wrapper) is not None)
        card.settings_button.setVisible(bool(wrapper.has_settings()))
        if not wrapper.enabled:
            card.set_state("none", S.CARD_STATUS_TURNED_OFF)
            return folder_asked
        if not wrapper.ready:
            if folder_asked:
                card.set_state("warning", S.FOLDER_ASKED_NEXT)
                return folder_asked
            card.set_state(
                "warning",
                S.CARD_STATUS_NEEDS_FILE
                if wants_file(wrapper)
                else S.CARD_STATUS_NEEDS_FOLDER,
            )
            card.folder_button.hide()
            card.body.addWidget(self._folder_block(wrapper))
            return True
        if reading:
            card.set_state("busy", S.CARD_STATUS_READING.format(game=name))
            return folder_asked
        if name in self._failed:
            card.set_state("warning", S.CARD_STATUS_FAILED.format(game=name))
            card.body.addWidget(self._failed_block(wrapper, self._failed[name]))
            return folder_asked
        count = self._profile_count(wrapper)
        time = self._read_times.get(name, "")
        if count == 0 and name in self._read_times:
            card.set_state("warning", S.CARD_STATUS_NO_BINDINGS.format(time=time))
            card.body.addWidget(self._no_bindings_block(wrapper, path))
            return folder_asked
        if count:
            text = S.CARD_STATUS_READ.format(
                count=count, profiles=S.plural(count, S.PROFILES), time=time
            )
            card.set_state("ok", text if time else text.split(" · read")[0])
            return folder_asked
        card.set_state("none", S.CARD_STATUS_NOT_READ)
        return folder_asked

    def _folder_block(self, wrapper: Any) -> QFrame:
        block = QFrame()
        block.setObjectName("folderBlock")
        layout = QVBoxLayout(block)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        file_mode = wants_file(wrapper)
        field = primary_path_field(wrapper)
        candidates = suggested_paths(wrapper)
        for index, candidate in enumerate(candidates):
            row = QHBoxLayout()
            row.setSpacing(10)
            column = QVBoxLayout()
            column.setSpacing(1)
            heading = S.FOLDER_FOUND if index == 0 else S.FOLDER_ALSO_FOUND
            path_row = QHBoxLayout()
            path_row.setSpacing(6)
            if index == 0:
                tick = QLabel()
                tick.setPixmap(
                    qta.icon("fa5s.check-circle", color=COLOUR_OK).pixmap(QSize(12, 12))
                )
                path_row.addWidget(tick)
            path_row.addWidget(_label(heading, "muted", wrap=False))
            path_row.addWidget(_label(str(candidate), "candidatePath", wrap=False), 1)
            column.addLayout(path_row)
            facts = candidate_facts(candidate)
            if facts:
                column.addWidget(_label(facts))
            row.addLayout(column, 1)
            if index == 0:
                text = (
                    S.FOLDER_USE_FILE_AND_READ if file_mode else S.FOLDER_USE_AND_READ
                )
            else:
                text = S.FOLDER_USE_INSTEAD
            row.addWidget(
                _button(
                    text,
                    lambda c=candidate: self.use_path(wrapper, c),
                    primary=index == 0,
                ),
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )
            layout.addLayout(row)
        choose_text = S.CARD_CHOOSE_FILE if file_mode else S.CARD_CHOOSE_FOLDER
        if candidates:
            row = QHBoxLayout()
            row.addWidget(_label(S.FOLDER_NOT_RIGHT, wrap=False))
            link = QPushButton(choose_text)
            link.setObjectName("setupLink")
            link.setCursor(Qt.CursorShape.PointingHandCursor)
            link.clicked.connect(lambda: self.choose_folder(wrapper))
            row.addWidget(link)
            row.addStretch(1)
            layout.addLayout(row)
        else:
            none_text = S.FILE_NONE_FOUND if file_mode else S.FOLDER_NONE_FOUND
            hint = ""
            if field is not None and field[1].description:
                hint = f" {field[1].description}"
            layout.addWidget(_label(none_text.format(game=wrapper.name) + hint))
            layout.addWidget(
                _button(choose_text, lambda: self.choose_folder(wrapper), primary=True),
                0,
                Qt.AlignmentFlag.AlignLeft,
            )
        problem = self._folder_problems.get(wrapper.name)
        if problem:
            layout.addWidget(
                _label(
                    S.PANEL_PATH_PROBLEM.format(game=wrapper.name, detail=problem),
                    "problem",
                )
            )
        return block

    def _notice_block(self, tone: str = "warning") -> tuple[QFrame, QVBoxLayout]:
        block = QFrame()
        block.setObjectName("noticeBlock")
        block.setProperty("tone", tone)
        layout = QVBoxLayout(block)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        return block, layout

    def _no_bindings_block(self, wrapper: Any, path: Path | None) -> QFrame:
        block, layout = self._notice_block()
        body = (
            S.NO_BINDINGS_BODY.format(path=path)
            if path
            else S.NO_BINDINGS_BODY_NO_PATH.format(game=wrapper.name)
        )
        layout.addWidget(_label(body))
        layout.addWidget(
            _button(
                S.CARD_CHOOSE_FILE if wants_file(wrapper) else S.CARD_CHOOSE_FOLDER,
                lambda: self.choose_folder(wrapper),
            ),
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        return block

    def _failed_block(self, wrapper: Any, detail: str) -> QFrame:
        block, layout = self._notice_block()
        path = current_path(wrapper)
        if path is not None and not path.exists():
            body = S.READ_FAILED_BODY.format(
                game=wrapper.name, detail=S.READ_FAILED_PATH_GONE.format(path=path)
            )
        else:
            body = S.READ_FAILED_BODY_PLAIN.format(game=wrapper.name)
        layout.addWidget(_label(f"{body} {S.READ_FAILED_KEPT}"))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(
            _button(
                S.CARD_CHOOSE_FILE if wants_file(wrapper) else S.CARD_CHOOSE_FOLDER,
                lambda: self.choose_folder(wrapper),
            )
        )
        row.addWidget(_button(S.CARD_READ_AGAIN, lambda: self.read_games([wrapper])))
        if detail:
            details = QPushButton(S.READ_FAILED_DETAILS)
            details.setObjectName("setupLink")
            details_label = _label(detail)
            details_label.hide()
            details.clicked.connect(
                lambda: details_label.setVisible(not details_label.isVisible())
            )
            row.addWidget(details)
            row.addStretch(1)
            layout.addLayout(row)
            layout.addWidget(details_label)
        else:
            row.addStretch(1)
            layout.addLayout(row)
        return block

    # ── Results card ──

    def _rebuild_results(self) -> None:
        _clear_layout(self.results_layout)
        if not self.wrappers or not self.appState.profile_wrappers:
            self.results_card.hide()
            return
        summary = self.summary()
        profiles = len(self.appState.profile_wrappers)
        found = summary.found
        self.results_card.show()
        if not found:
            self.results_layout.addWidget(
                _label(S.RESULTS_NO_CONTROLLERS, "resultsTitle")
            )
            return
        self.results_layout.addWidget(
            _label(
                S.RESULTS_TITLE.format(
                    controllers=S.counted(len(found), S.CONTROLLERS),
                    profiles=S.counted(profiles, S.PROFILES),
                ),
                "resultsTitle",
            )
        )
        needs = summary.needs
        if needs:
            names = " · ".join(summary.statuses[g].name or g for g in needs)
            self._results_row(
                len(needs),
                S.RESULTS_NEED_TEMPLATE_ONE
                if len(needs) == 1
                else S.RESULTS_NEED_TEMPLATE,
                names,
                "warning",
            )
        ready = summary.ready
        if ready:
            names = " · ".join(summary.statuses[g].name or g for g in ready)
            self._results_row(
                len(ready), f"{S.RESULTS_READY} {S.RESULTS_READY_HINT}", names, "ok"
            )
        no_diagram = summary.no_diagram
        if no_diagram:
            from joystick_diagrams.device_status import reason_text
            from joystick_diagrams.ui.controllers_page import merged_name

            parts = []
            for guid in no_diagram:
                info = summary.statuses[guid]
                if info.state.value == "merged":
                    reason = reason_text(
                        "merged_into", merged_name=merged_name(info, summary.statuses)
                    )
                else:
                    reason = reason_text(info.reason, info.template_name)
                name = info.name or guid
                parts.append(f"{name} ({SC.lower_first(reason)})" if reason else name)
            self._results_row(
                len(no_diagram),
                f"{S.RESULTS_NO_DIAGRAM} {S.RESULTS_NO_DIAGRAM_HINT}",
                " · ".join(parts),
                "none",
            )
        if needs:
            self.results_layout.addWidget(_label(S.RESULTS_TEMPLATE_DEFINITION))

    def _results_row(self, count: int, text: str, detail: str, tone: str) -> None:
        row = QHBoxLayout()
        row.setSpacing(12)
        number = _label(str(count), "bigCount", wrap=False)
        number.setProperty("tone", tone)
        number.setFixedWidth(36)
        number.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        row.addWidget(number, 0, Qt.AlignmentFlag.AlignTop)
        column = QVBoxLayout()
        column.setSpacing(2)
        column.addWidget(_label(text, "blockTitle"))
        if detail:
            column.addWidget(_label(detail))
        row.addLayout(column, 1)
        self.results_layout.addLayout(row)

    def results_text(self) -> str:
        """Every label in the results card, for tests and screen readers."""
        texts = []
        for label in self.results_card.findChildren(QLabel):
            if label.text():
                texts.append(label.text())
        return "\n".join(texts)

    # ── Actions ──

    def read_games(self, wrappers: list[Any] | None = None) -> None:
        self.read_requested.emit(wrappers)

    def use_path(self, wrapper: Any, path: Path) -> None:
        field = primary_path_field(wrapper)
        if field is None:
            return
        problem = apply_path(wrapper, field[0], path)
        if problem:
            self._folder_problems[wrapper.name] = problem
            self.populate_plugin_cards()
            return
        self._folder_problems.pop(wrapper.name, None)
        self.populate_plugin_cards()
        if wrapper.ready:
            self.read_games([wrapper])

    def choose_folder(self, wrapper: Any) -> None:
        path = ask_for_path(self, wrapper)
        if path is not None:
            self.use_path(wrapper, path)

    def set_game_enabled(self, wrapper: Any, enabled: bool) -> None:
        wrapper.enabled = enabled
        try:
            self.appState.reprocess_profiles_with_notice(S.SAVED)
        except Exception as error:  # noqa: BLE001
            _logger.error(
                f"Reprocessing after a game change failed: {error}", exc_info=True
            )
        self.populate_plugin_cards()

    def show_settings(self, wrapper: Any) -> None:
        self.close_settings()
        panel = GameSettingsPanel(wrapper)
        panel.changed.connect(self.populate_plugin_cards)
        panel.close_requested.connect(self.close_settings)
        self.side_panel.addWidget(panel)
        self._settings_for = wrapper.name

    def close_settings(self) -> None:
        self._settings_for = None
        _clear_layout(self.side_panel)

    def remove_game(self, wrapper: Any) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(S.REMOVE_TITLE.format(game=wrapper.name))
        box.setText(S.REMOVE_TITLE.format(game=wrapper.name))
        box.setInformativeText(S.REMOVE_BODY)
        remove = box.addButton(
            S.REMOVE_CONFIRM.format(game=wrapper.name),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        box.addButton(S.CANCEL, QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not remove:
            return
        from joystick_diagrams.plugins.plugin_installer import uninstall_plugin
        from joystick_diagrams.ui.plugin_install_flow import reload_plugin_manager

        path = self.appState.plugin_manager.get_user_plugin_path(wrapper.name)
        if not path:
            return
        try:
            uninstall_plugin(wrapper.name, path, "parser")
        except Exception as error:  # noqa: BLE001
            _logger.error(f"Removing {wrapper.name} failed: {error}", exc_info=True)
            show_problem(
                self,
                S.REMOVE_FAILED.format(game=wrapper.name),
                S.REMOVE_FAILED_TEXT,
                str(error),
            )
            return
        reload_plugin_manager(self.appState, "parser")
        self.appState.reprocess_profiles_with_notice(S.SAVED)

    # ── Adding games ──

    def fetch_catalog(self) -> None:
        from joystick_diagrams.ui.plugin_store_dialog import _FetchWorker

        self._catalog_requested = True
        self.picker.set_loading()
        self._catalog_worker = _FetchWorker()
        self._catalog_worker.signals.finished.connect(self._on_catalog)
        self._pool.start(self._catalog_worker)

    def _on_catalog(self, catalog: Any) -> None:
        from joystick_diagrams.plugins import plugin_catalog as pc

        if catalog is None:
            self.picker.set_unavailable()
            self.state_changed.emit()
            return
        if remember_catalog_flags(catalog):
            self.populate_plugin_cards()
        installed = pc.installed_index(
            self.appState.plugin_manager, self.appState.output_plugin_manager
        )
        entries = [
            status.entry
            for status in pc.compute_status(catalog, installed)
            if status.status is pc.CatalogStatus.AVAILABLE
            and status.compatible
            and status.entry.type == "parser"
        ]
        self.picker.set_entries(entries)
        self.state_changed.emit()

    def add_games(self, entries: list[Any]) -> None:
        from joystick_diagrams.ui.plugin_install_flow import install_from_catalog

        added = False
        for entry in entries:
            if install_from_catalog(entry, self.appState, self):
                added = True
        if not added:
            self.populate_plugin_cards()

    def add_game_from_file(self) -> None:
        result, _ = QFileDialog.getOpenFileName(
            self,
            S.PICKER_ADD_FROM_FILE_TITLE,
            str(Path.home()),
            S.PICKER_ADD_FROM_FILE_FILTER,
        )
        if result:
            from joystick_diagrams.ui.plugin_install_flow import (
                install_from_local_source,
            )

            if (
                install_from_local_source(Path(result), self.appState, self, "parser")
                is None
            ):
                self.populate_plugin_cards()

    def open_game_list(self) -> None:
        from joystick_diagrams.ui.plugin_store_dialog import PluginStoreDialog

        dialog = PluginStoreDialog(self)
        dialog.catalog_changed.connect(self.populate_plugin_cards)
        dialog.catalog_changed.connect(self.check_plugin_updates)
        dialog.exec()

    # ── Game updates ──

    def check_plugin_updates(self) -> None:
        from joystick_diagrams.ui.plugin_store_dialog import _FetchWorker

        self._update_worker = _FetchWorker()
        self._update_worker.signals.finished.connect(self._on_update_catalog)
        self._pool.start(self._update_worker)

    def _on_update_catalog(self, catalog: Any) -> None:
        from joystick_diagrams.plugins import plugin_catalog as pc

        if catalog is None:
            return
        if remember_catalog_flags(catalog):
            self.populate_plugin_cards()
        installed = pc.installed_index(
            self.appState.plugin_manager, self.appState.output_plugin_manager
        )
        updates = pc.available_updates(pc.compute_status(catalog, installed))
        if not updates:
            self.update_notice.hide()
            return
        signature = ",".join(sorted(f"{u.entry.id}:{u.entry.version}" for u in updates))
        if db_settings.get_setting(PLUGIN_UPDATES_DISMISSED_KEY) == signature:
            return
        self._update_signature = signature
        self._update_count = len(updates)
        self.update_label.setText(
            S.GAME_UPDATES_AVAILABLE.format(
                count=len(updates), games=S.plural(len(updates), S.GAMES)
            )
        )
        self.update_notice.show()

    def _dismiss_updates(self) -> None:
        if self._update_signature:
            db_settings.add_update_setting_value(
                PLUGIN_UPDATES_DISMISSED_KEY, self._update_signature
            )
        self.update_notice.hide()


__all__ = ["SetupPage", "suggested_paths"]

if __name__ == "__main__":
    pass
