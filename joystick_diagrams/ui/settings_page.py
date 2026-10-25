"""Settings (the cog at the end of the stage strip): General and Other apps.

General holds the app-wide choices that don't belong to one stage: the date on
diagrams, reading the games when the app opens, and what to do when a
controller listed twice has two bindings on one control. Pointers lead to the
stage that owns the rest (games live in 1. Setup, modifier display in
4. Diagrams › Appearance).

Other apps lists the output plugins (in code) that get the diagrams after each
export. Adding one goes through ``plugin_install_flow`` (the same security check
as a game); success is one inline line, never a dialog.
"""

import logging
import webbrowser
from datetime import datetime
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import utils, workflow_settings
from joystick_diagrams.app_state import AppState
from joystick_diagrams.conflict_strategy import (
    ALIAS_CONFLICT_STRATEGY_KEY,
    AliasConflictStrategy,
    get_alias_strategy,
)
from joystick_diagrams.db.db_settings import add_update_setting_value, get_setting
from joystick_diagrams.ui import strings_settings as S
from joystick_diagrams.ui.widgets.confirm import confirm, show_problem

_logger = logging.getLogger(__name__)

DATE_FORMAT_SETTING_KEY = "export_date_format"
DEFAULT_DATE_FORMAT = "%d/%m/%Y"

DATE_FORMAT_OPTIONS = [
    ("%d/%m/%Y", "DD/MM/YYYY"),
    ("%m/%d/%Y", "MM/DD/YYYY"),
    ("%Y-%m-%d", "YYYY-MM-DD"),
    ("%d-%m-%Y", "DD-MM-YYYY"),
    ("%d %b %Y", "DD Mon YYYY"),
    ("%B %d, %Y", "Month DD, YYYY"),
    ("%Y/%m/%d", "YYYY/MM/DD"),
]

ALIAS_STRATEGY_OPTIONS = [
    (AliasConflictStrategy.CONCATENATE, S.LISTED_TWICE_CONCATENATE),
    (AliasConflictStrategy.MODIFIER, S.LISTED_TWICE_MODIFIER),
]

PAGE_QSS = """
QLabel#settingsHelp { color: #9AA0A6; font-size: 12px; }
QLabel#settingsSuccess { color: #34D399; font-size: 12px; }
QLabel#settingsWarning { color: #F59E0B; font-size: 12px; }
QPushButton#settingsLink {
    background: transparent; border: none; color: #8AB4F8; padding: 2px 0px;
    text-align: left; font-size: 12px; font-weight: 700; text-transform: none;
}
QPushButton#settingsLink:hover { text-decoration: underline; }
"""


def _help(text: str, name: str = "settingsHelp") -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    label.setWordWrap(True)
    return label


def _link(text: str, handler) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("settingsLink")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFlat(True)
    button.clicked.connect(lambda _checked=False: handler())
    return button


class SettingsPage(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.appState = AppState()
        self.setStyleSheet(PAGE_QSS)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setProperty("class", "settings-nav")
        for icon_name, label in (
            ("fa5s.cog", S.NAV_GENERAL),
            ("fa5s.plug", S.NAV_OTHER_APPS),
        ):
            item = QListWidgetItem(qta.icon(icon_name, color="#9AA0A6"), label)
            item.setSizeHint(QSize(0, 44))
            self.nav_list.addItem(item)
        root_layout.addWidget(self.nav_list)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_general_tab())
        self.stack.addWidget(self._create_other_apps_tab())
        root_layout.addWidget(self.stack, 1)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def refresh(self):
        """Refresh data-dependent tabs when returning to this page."""
        self.auto_read_cb.blockSignals(True)
        self.auto_read_cb.setChecked(workflow_settings.get_auto_read_on_launch())
        self.auto_read_cb.blockSignals(False)
        self._populate_app_cards()

    # ── General ──

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 4, 0, 0)

        self.date_format_combo = QComboBox()
        self.date_format_combo.setProperty("class", "view-binds-list")
        self.date_format_combo.setMinimumWidth(220)
        now = datetime.now()
        current_format = get_setting(DATE_FORMAT_SETTING_KEY) or DEFAULT_DATE_FORMAT
        selected_index = 0
        for i, (fmt, label) in enumerate(DATE_FORMAT_OPTIONS):
            self.date_format_combo.addItem(f"{label}  ({now.strftime(fmt)})", fmt)
            if fmt == current_format:
                selected_index = i
        self.date_format_combo.setCurrentIndex(selected_index)
        self.date_format_combo.currentIndexChanged.connect(self._on_date_format_changed)
        date_row = QHBoxLayout()
        date_row.addWidget(self.date_format_combo)
        date_row.addStretch(1)
        form.addRow(_help(S.DATE_ON_DIAGRAMS), date_row)

        self.auto_read_cb = QCheckBox(S.AUTO_READ)
        self.auto_read_cb.setToolTip(S.AUTO_READ_TIP)
        self.auto_read_cb.setChecked(workflow_settings.get_auto_read_on_launch())
        self.auto_read_cb.toggled.connect(workflow_settings.set_auto_read_on_launch)
        form.addRow("", self.auto_read_cb)

        self.alias_strategy_combo = QComboBox()
        self.alias_strategy_combo.setProperty("class", "view-binds-list")
        self.alias_strategy_combo.setMinimumWidth(320)
        current_alias = get_alias_strategy()
        for i, (value, label) in enumerate(ALIAS_STRATEGY_OPTIONS):
            self.alias_strategy_combo.addItem(label, value.value)
            if value == current_alias:
                self.alias_strategy_combo.setCurrentIndex(i)
        self.alias_strategy_combo.currentIndexChanged.connect(
            self._on_alias_strategy_changed
        )
        listed_twice = _help(S.LISTED_TWICE)
        listed_twice.setMaximumWidth(260)
        alias_row = QHBoxLayout()
        alias_row.addWidget(self.alias_strategy_combo)
        alias_row.addStretch(1)
        form.addRow(listed_twice, alias_row)
        layout.addLayout(form)

        for text, button_text, handler in (
            (S.MODIFIERS_POINTER, S.GO_TO_APPEARANCE, self._open_appearance),
            (S.GAMES_POINTER, S.GO_TO_SETUP, self._open_setup),
        ):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(_help(text), 1)
            button = _link(button_text, handler)
            row.addWidget(button)
            layout.addLayout(row)
            if handler == self._open_appearance:
                self.open_appearance_button = button

        layout.addStretch(1)
        return tab

    def _open_appearance(self):
        from joystick_diagrams.ui.stage_contract import (
            PAYLOAD_SECTION,
            SECTION_APPEARANCE,
            STAGE_DIAGRAMS,
        )

        main_window = self.appState.main_window
        if main_window is not None:
            main_window.go_to_stage(
                STAGE_DIAGRAMS, {PAYLOAD_SECTION: SECTION_APPEARANCE}
            )

    def _open_setup(self):
        from joystick_diagrams.ui.stage_contract import STAGE_SETUP

        main_window = self.appState.main_window
        if main_window is not None:
            main_window.go_to_stage(STAGE_SETUP)

    def _on_date_format_changed(self, index: int):
        fmt = self.date_format_combo.currentData()
        if fmt:
            add_update_setting_value(DATE_FORMAT_SETTING_KEY, fmt)

    # Process-time settings (those that bake into the merged profile state)
    # call appState.reprocess_profiles_with_notice(...) after persisting.
    def _on_alias_strategy_changed(self, index: int):
        value = self.alias_strategy_combo.currentData()
        if value:
            add_update_setting_value(ALIAS_CONFLICT_STRATEGY_KEY, value)
            self.appState.reprocess_profiles_with_notice(S.SAVED_BINDINGS_UPDATED)

    # ── Other apps ──

    def _create_other_apps_tab(self) -> QWidget:
        from joystick_diagrams.ui.widgets.drop_zone import DropZoneWidget

        tab = QWidget()
        tab_layout = QHBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(_help(S.OTHER_APPS_INTRO))

        self.apps_notice = _help("", "settingsSuccess")
        self.apps_notice.hide()
        layout.addWidget(self.apps_notice)
        self.conflict_label = _help("", "settingsWarning")
        self.conflict_label.hide()
        layout.addWidget(self.conflict_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        for text, icon_name, handler in (
            (S.ADD_APP_FROM_FILE, "fa5s.file-import", self._add_app_from_file),
            (S.ADD_APP_FROM_WEB, "fa5s.link", self._add_app_from_web),
            (S.OPEN_APPS_FOLDER, "fa5s.folder-open", self._open_apps_folder),
        ):
            button = QPushButton(text)
            button.setIcon(qta.icon(icon_name, color="white"))
            button.setProperty("class", "plugin-setup-button")
            button.clicked.connect(lambda _checked=False, h=handler: h())
            button_row.addWidget(button)
        drop_zone = DropZoneWidget(S.DROP_APP_HERE, compact=True)
        drop_zone.file_dropped.connect(self._add_app)
        button_row.addWidget(drop_zone)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cards_container = QWidget()
        self._app_cards_layout = QVBoxLayout(cards_container)
        self._app_cards_layout.setSpacing(4)
        self._app_cards_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(cards_container)
        layout.addWidget(scroll, 1)
        tab_layout.addWidget(left, 1)

        self._side_panel = QVBoxLayout()
        self._side_panel.setContentsMargins(0, 0, 0, 0)
        tab_layout.addLayout(self._side_panel)

        self._populate_app_cards()
        return tab

    @staticmethod
    def _trust_status(name: str) -> str:
        from joystick_diagrams.db.db_plugin_trust import get_trust_reason
        from joystick_diagrams.ui.widgets.plugin_card import (
            TRUST_SIGNED,
            TRUST_UNTRUSTED,
            TRUST_USER_ACCEPTED,
        )

        reason = get_trust_reason(name, "output")
        if reason == "signature_valid":
            return TRUST_SIGNED
        if reason == "user_accepted":
            return TRUST_USER_ACCEPTED
        return TRUST_UNTRUSTED

    def _populate_app_cards(self):
        from joystick_diagrams.ui.widgets.plugin_card import TRUST_BUNDLED, PluginCard

        while self._app_cards_layout.count():
            item = self._app_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        manager = self.appState.output_plugin_manager
        conflicts = getattr(manager, "conflicts", None) if manager else None
        if conflicts:
            names = ", ".join(name for name, _ in conflicts)
            self.conflict_label.setText(S.NAME_TAKEN.format(names=names))
            self.conflict_label.show()
        else:
            self.conflict_label.hide()

        wrappers = list(getattr(manager, "plugin_wrappers", None) or [])
        if not wrappers:
            self._app_cards_layout.addWidget(_help(S.OTHER_APPS_EMPTY))
        for wrapper in wrappers:
            is_user = manager.is_user_plugin(wrapper.name)
            trust = self._trust_status(wrapper.name) if is_user else TRUST_BUNDLED
            card = PluginCard(wrapper, is_user_plugin=is_user, trust_status=trust)
            card.config_requested.connect(self._show_side_panel)
            if is_user:
                card.uninstall_requested.connect(self._remove_app)
            self._app_cards_layout.addWidget(card)
        self._app_cards_layout.addStretch(1)

    def _show_side_panel(self, wrapper) -> None:
        from joystick_diagrams.ui.setup_page import PAGE_QSS as SETUP_QSS
        from joystick_diagrams.ui.setup_page import GameSettingsPanel

        self._clear_side_panel()
        panel = GameSettingsPanel(wrapper, self, for_app=True)
        panel.setStyleSheet(SETUP_QSS)
        panel.changed.connect(self._refresh_card_status)
        panel.close_requested.connect(self._clear_side_panel)
        self._side_panel.addWidget(panel)

    def _clear_side_panel(self) -> None:
        while self._side_panel.count():
            item = self._side_panel.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh_card_status(self):
        for i in range(self._app_cards_layout.count()):
            item = self._app_cards_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget is not None and hasattr(widget, "refresh_status"):
                widget.refresh_status()

    def _show_notice(self, text: str) -> None:
        self.apps_notice.setText(text)
        self.apps_notice.show()

    def _add_app_from_file(self):
        result, _ = QFileDialog.getOpenFileName(
            self, S.ADD_APP_FROM_FILE_TITLE, str(Path.home()), S.ADD_APP_FILE_FILTER
        )
        if result:
            self._add_app(Path(result))

    def _add_app_from_web(self):
        url, ok = QInputDialog.getText(
            self, S.ADD_APP_FROM_WEB_TITLE, S.ADD_APP_FROM_WEB_LABEL
        )
        if ok and url.strip():
            self._add_app(url.strip())

    def _add_app(self, source: Path | str):
        from joystick_diagrams.ui.plugin_install_flow import install_from_local_source

        name = install_from_local_source(source, self.appState, self, "output")
        if name is None:
            return
        self._populate_app_cards()
        self._show_notice(S.APP_ADDED.format(app=name))

    def _remove_app(self, name: str):
        if not confirm(
            self,
            S.REMOVE_TITLE.format(app=name),
            S.REMOVE_BODY,
            S.REMOVE_CONFIRM.format(app=name),
            S.CANCEL,
        ):
            return

        from joystick_diagrams.plugins.plugin_installer import uninstall_plugin
        from joystick_diagrams.ui.plugin_install_flow import reload_plugin_manager

        path = self.appState.output_plugin_manager.get_user_plugin_path(name)
        if not path:
            return
        try:
            uninstall_plugin(name, path, "output")
        except Exception as error:  # noqa: BLE001 - shown behind Details
            _logger.error(f"Removing {name} failed: {error}", exc_info=True)
            show_problem(
                self,
                S.REMOVE_FAILED_TITLE.format(app=name),
                S.REMOVE_FAILED_TEXT,
                str(error),
            )
            return
        reload_plugin_manager(self.appState, "output")
        self._populate_app_cards()
        self._show_notice(S.APP_REMOVED.format(app=name))

    def _open_apps_folder(self):
        webbrowser.open(str(utils.user_output_plugins_root()))


if __name__ == "__main__":
    pass
