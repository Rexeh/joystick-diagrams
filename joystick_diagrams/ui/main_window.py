"""The four-stage shell: 1. Setup · 2. Controllers · 3. Bindings · 4. Diagrams.

``MainWindow`` owns the stage strip (``StageStrip``), the reserved banner slot,
the page stack, the pinned footer and the status bar, and talks to the four
stage pages only through the contract in ``ui/stage_contract.py``:
``refresh()``, ``stage_status()``, ``next_action()``, ``request_stage``.

Stages 1 and 2 are ``ui/setup_page.SetupPage`` and
``ui/controllers_page.ControllersPage``; stages 3 and 4 are imported lazily from
``ui/bindings_page`` and ``ui/diagrams_page`` and replaced by a
``PlaceholderStagePage`` when they cannot be imported, so the app always starts.

Landing: no game set up → 1. Setup; otherwise the last stage used
(``workflow_settings.get_last_stage()``), 4. Diagrams for an upgrader who never
recorded one. The games are read again in the background after the window shows
(``workflow_settings.get_auto_read_on_launch()``); the read never blocks, never
opens a modal and never moves the page: tab 1 shows "⟳ Reading…", a popover
under it says what is kept, a failure turns tab 1 amber and puts
[Choose folder…] [Read again] in the banner slot. ``read_in_progress``,
``read_started`` and ``read_finished(ReadOutcome)`` let stage 4 queue an export.

Pages survive re-reads: ``_invalidate_data_pages`` calls ``refresh()`` on the
live pages instead of destroying them; ``shutdown()`` is called on pages that
expose it only when the window closes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QCoreApplication, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams import version, workflow_settings
from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import strings_shell as S
from joystick_diagrams.ui import ui_consts
from joystick_diagrams.ui.stage_contract import (
    STAGE_BINDINGS,
    STAGE_CONTROLLERS,
    STAGE_COUNT,
    STAGE_DIAGRAMS,
    STAGE_SETUP,
    STAGE_TITLES,
    NextAction,
    ReadOutcome,
    StageStatus,
)
from joystick_diagrams.ui.stage_shell import (
    BannerSlot,
    GameReader,
    PlaceholderStagePage,
    ReadPopover,
    StageFooter,
    StageStrip,
    dismiss_new_controller,
    dismissed_new_controllers,
    is_first_run_done,
    mark_first_run_done,
    mark_upgrade_notice_shown,
    now_time_text,
    upgrade_notice_shown,
)
from joystick_diagrams.utils import data_root

_logger = logging.getLogger(__name__)

PageFactory = Callable[[], QWidget]
BANNER_KEY_READ_FAILED = "read-failed"
BANNER_KEY_UPGRADE = "upgrade"
POPOVER_HIDE_DELAY_MS = 6000


class MainWindow(QMainWindow):
    read_started = Signal(list)  # game names
    read_finished = Signal(object)  # ReadOutcome
    stage_changed = Signal(int)

    def __init__(
        self,
        *args,
        page_factories: dict[int, PageFactory] | None = None,
        auto_read: bool = True,
        check_updates: bool = True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.app = QCoreApplication.instance()
        self.appState = AppState()
        self.appState.main_window = self
        self._auto_read_allowed = auto_read
        self._check_updates = check_updates
        self._shown_once = False
        self._current_stage: int | None = None
        self._pages: list[QWidget | None] = [None] * STAGE_COUNT
        self._settings_page: QWidget | None = None
        self._status_text = S.STATUS_APP_UP_TO_DATE
        self._launch_read = False
        self._last_read_time: str | None = None
        self._debug_action: QAction | None = None
        self._cross_refreshing = False

        self.setWindowIcon(QIcon(ui_consts.JD_ICON))
        self.setWindowTitle(
            S.WINDOW_TITLE.format(version=version.get_current_version())
        )
        self.resize(1100, 900)
        self.setMinimumSize(QSize(800, 600))

        self._build_shell()
        self._build_status_bar()

        self.reader = GameReader(self.appState, self)
        self.reader.started.connect(self._on_read_started)
        self.reader.finished.connect(self._on_read_finished)
        self.read_popover = ReadPopover(self)
        self.read_popover.read_again.connect(self.start_read)
        self.read_popover.toggle_automatic.connect(
            workflow_settings.set_auto_read_on_launch
        )
        self._popover_timer = QTimer(self)
        self._popover_timer.setSingleShot(True)
        self._popover_timer.timeout.connect(self.read_popover.hide)

        factories = self._default_factories()
        if page_factories:
            factories.update(page_factories)
        for index in range(STAGE_COUNT):
            self._install_page(index, factories[index])

        landing = self._initial_stage()
        self.go_to_stage(landing, record=False)
        self._maybe_show_upgrade_notice()

    # ── Construction ──

    def _build_shell(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_menu_row())
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("jdMenuDivider")
        divider.setFixedHeight(1)
        root.addWidget(divider)

        self.strip = StageStrip()
        self.strip.stage_selected.connect(self._on_stage_selected)
        self.strip.settings_clicked.connect(self.load_settings_page)
        root.addWidget(self.strip)

        self.banner = BannerSlot()
        root.addWidget(self.banner)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.footer = StageFooter()
        root.addWidget(self.footer)

    def _build_menu_row(self) -> QWidget:
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(4)

        help_btn = QToolButton()
        help_btn.setText(S.MENU_HELP)
        help_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        help_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.setAutoRaise(True)
        help_btn.setFixedHeight(26)
        help_btn.setObjectName("jdMenuHelp")
        help_btn.setMenu(self._build_help_menu(help_btn))
        row.addWidget(help_btn)
        row.addStretch(1)

        def link(icon_name, icon_color, text, tooltip, handler, variant="link"):
            btn = QToolButton()
            btn.setIcon(qta.icon(icon_name, color=icon_color))
            btn.setIconSize(QSize(14, 14))
            btn.setText(text)
            btn.setToolTip(tooltip)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setFixedHeight(26)
            btn.setObjectName("jdMenuLinkCta" if variant == "cta" else "jdMenuLink")
            btn.clicked.connect(handler)
            return btn

        row.addWidget(
            link(
                "fa5s.globe",
                "#9AA0A6",
                S.LINK_WEBSITE,
                S.LINK_WEBSITE_TIP,
                self._open_website,
            )
        )
        row.addWidget(
            link(
                "fa5b.github",
                "#9AA0A6",
                S.LINK_GITHUB,
                S.LINK_GITHUB_TIP,
                self._open_github,
            )
        )
        row.addWidget(
            link(
                "fa5b.discord",
                "#9AA0A6",
                S.LINK_DISCORD,
                S.LINK_DISCORD_TIP,
                self._open_discord,
            )
        )
        row.addWidget(
            link(
                "fa5s.mug-hot",
                "#F59E0B",
                S.LINK_COFFEE,
                S.LINK_COFFEE_TIP,
                self._open_buymeacoffee,
                variant="cta",
            )
        )
        return row_widget

    def _build_help_menu(self, parent: QWidget) -> QMenu:
        menu = QMenu(parent)
        support_action = QAction(S.MENU_SUPPORT, self)
        support_action.setToolTip(S.MENU_SUPPORT_TIP)
        support_action.triggered.connect(self._open_discord)
        menu.addAction(support_action)
        menu.addSeparator()
        open_logs_action = QAction(S.MENU_OPEN_LOG_FOLDER, self)
        open_logs_action.triggered.connect(self._open_logs_folder)
        menu.addAction(open_logs_action)
        self._debug_action = QAction(S.MENU_DETAILED_LOGGING, self)
        self._debug_action.setCheckable(True)
        self._debug_action.setChecked(False)
        self._debug_action.triggered.connect(self._toggle_debug_mode)
        menu.addAction(self._debug_action)
        menu.addSeparator()
        check_updates_action = QAction(S.MENU_CHECK_FOR_UPDATES, self)
        check_updates_action.triggered.connect(self._check_for_updates)
        menu.addAction(check_updates_action)
        about_action = QAction(S.MENU_ABOUT, self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)
        return menu

    def _build_status_bar(self) -> None:
        self.progressBar = QProgressBar()
        self.progressBar.setFixedWidth(260)
        self.progressBar.setTextVisible(False)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.statusLabel = QLabel(self._status_text)
        self.statusBar().addPermanentWidget(self.statusLabel, 1)
        self.statusBar().addPermanentWidget(self.progressBar, 0)

    # ── Pages ──

    def _default_factories(self) -> dict[int, PageFactory]:
        return {
            STAGE_SETUP: self._make_setup_page,
            STAGE_CONTROLLERS: self._make_controllers_page,
            STAGE_BINDINGS: lambda: self._make_lazy_page(
                STAGE_BINDINGS, "joystick_diagrams.ui.bindings_page", "BindingsPage"
            ),
            STAGE_DIAGRAMS: lambda: self._make_lazy_page(
                STAGE_DIAGRAMS, "joystick_diagrams.ui.diagrams_page", "DiagramsPage"
            ),
        }

    def _make_setup_page(self) -> QWidget:
        from joystick_diagrams.ui.setup_page import SetupPage

        return SetupPage()

    def _make_controllers_page(self) -> QWidget:
        from joystick_diagrams.ui.controllers_page import ControllersPage

        return ControllersPage()

    def _make_lazy_page(self, stage: int, module_name: str, class_name: str) -> QWidget:
        """Import a stage page by name; a placeholder when it is not available."""
        import importlib

        try:
            module = importlib.import_module(module_name)
            page_class = getattr(module, class_name)
        except Exception as error:  # noqa: BLE001 - F3's page may not exist yet
            _logger.warning(
                f"{STAGE_TITLES[stage]} is not available ({error}); showing a placeholder"
            )
            return PlaceholderStagePage(stage, self.appState)
        try:
            return page_class()
        except Exception as error:  # noqa: BLE001 - never let one stage kill the shell
            _logger.error(
                f"{STAGE_TITLES[stage]} could not start: {error}", exc_info=True
            )
            return PlaceholderStagePage(stage, self.appState)

    def _install_page(self, index: int, factory: PageFactory) -> QWidget:
        try:
            page = factory()
        except Exception as error:  # noqa: BLE001 - keep the shell alive
            _logger.error(
                f"{STAGE_TITLES[index]} could not start: {error}", exc_info=True
            )
            page = PlaceholderStagePage(index, self.appState)
        self._pages[index] = page
        self.stack.addWidget(page)
        request = getattr(page, "request_stage", None)
        if request is not None:
            request.connect(self.go_to_stage)
        state_changed = getattr(page, "state_changed", None)
        if state_changed is not None:
            state_changed.connect(lambda i=index: self._on_page_state_changed(i))
        read_requested = getattr(page, "read_requested", None)
        if read_requested is not None:
            read_requested.connect(self.start_read)
        return page

    def page(self, index: int) -> QWidget:
        page = self._pages[index]
        assert page is not None
        return page

    @property
    def pages(self) -> list[QWidget]:
        return [page for page in self._pages if page is not None]

    @property
    def current_stage(self) -> int | None:
        return self._current_stage

    # ── Landing ──

    def games_set_up(self) -> bool:
        """At least one game is turned on and has its folder."""
        return bool(self.reader.readable_games())

    def _initial_stage(self) -> int:
        if not self.games_set_up():
            return STAGE_SETUP
        last = workflow_settings.get_last_stage()
        return STAGE_DIAGRAMS if last is None else last

    def _maybe_show_upgrade_notice(self) -> None:
        if upgrade_notice_shown():
            return
        if workflow_settings.get_last_stage() is not None or not self.games_set_up():
            mark_upgrade_notice_shown()
            return
        hidden = 0
        try:
            hidden = sum(
                1
                for row in self.appState.device_service.all_rows().values()
                if row.kind_reason == "legacy_hidden"
            )
        except Exception as error:  # noqa: BLE001 - the notice is a courtesy
            _logger.debug(f"Could not count hidden controllers: {error}")
        text = S.BANNER_UPGRADE
        if hidden:
            text += S.BANNER_UPGRADE_TURNED_OFF.format(
                count=hidden,
                controllers=S.plural(hidden, *S.CONTROLLERS),
                are=S.plural(hidden, "is", "are"),
            )
        self.show_banner(
            text,
            [(S.BANNER_UPGRADE_SHOW_ME, lambda: self.go_to_stage(STAGE_CONTROLLERS))],
            key=BANNER_KEY_UPGRADE,
        )
        mark_upgrade_notice_shown()

    # ── Navigation ──

    def go_to_stage(self, index: int, payload: dict | None = None, record: bool = True):
        """Show a stage. ``payload`` is handed to the page's ``handle_request``
        (or ``navigate``)."""
        if not 0 <= index < STAGE_COUNT:
            return
        page = self.page(index)
        self.strip.set_active(index)
        self.stack.setCurrentWidget(page)
        self._current_stage = index
        self._safe_call(page, "refresh")
        if payload:
            handler = (
                "handle_request" if hasattr(page, "handle_request") else "navigate"
            )
            self._safe_call(page, handler, payload)
        if record:
            workflow_settings.set_last_stage(index)
        if index == STAGE_DIAGRAMS and not is_first_run_done():
            mark_first_run_done()
        self.refresh_strip()
        self.stage_changed.emit(index)

    def _on_stage_selected(self, index: int) -> None:
        """A tab click. Clicking the already-open 1. Setup tab toggles the read
        popover (status, what is kept, Read again, automatic reading)."""
        if index == STAGE_SETUP and self._current_stage == STAGE_SETUP:
            if self.read_popover.isVisible():
                self._popover_timer.stop()
                self.read_popover.hide()
            else:
                self.show_read_popover()
            return
        self.go_to_stage(index)

    def load_settings_page(self) -> None:
        if self._settings_page is None:
            from joystick_diagrams.ui import settings_page

            self._settings_page = settings_page.SettingsPage()
            self.stack.addWidget(self._settings_page)
        else:
            self._safe_call(self._settings_page, "refresh")
        self.strip.set_active(None)
        self.stack.setCurrentWidget(self._settings_page)
        self._current_stage = None
        self.footer.set_actions(None)

    @property
    def setup_page(self) -> QWidget | None:
        return self._pages[STAGE_SETUP]

    def choose_template_for(self, guid: str) -> bool:
        """Open the template picker for ``guid`` over the current page (the page
        never moves) and refresh every stage when a template was chosen."""
        from joystick_diagrams.ui.template_picker import choose_template

        result = choose_template(self, guid)
        if result is None:
            return False
        self._invalidate_data_pages()
        return True

    # ── Strip and footer ──

    def stage_statuses(self) -> list[StageStatus]:
        statuses = []
        for index in range(STAGE_COUNT):
            page = self._pages[index]
            status = self._safe_call(page, "stage_status") if page is not None else None
            if not isinstance(status, StageStatus):
                status = StageStatus("none", "")
            statuses.append(status)
        return statuses

    def refresh_strip(self) -> None:
        self.strip.set_statuses(self.stage_statuses())
        self.refresh_footer()

    def refresh_footer(self) -> None:
        if self._current_stage is None:
            self.footer.set_actions(None)
            return
        page = self.page(self._current_stage)
        primary = self._safe_call(page, "next_action")
        secondary = self._safe_call(page, "secondary_action")
        hint = self._safe_call(page, "footer_hint")
        self.footer.set_actions(
            primary if isinstance(primary, NextAction) else None,
            secondary if isinstance(secondary, NextAction) else None,
            hint if isinstance(hint, str) else None,
        )

    def _on_page_state_changed(self, index: int | None = None) -> None:
        """A choice in 1. Setup or 2. Controllers (a template, No diagram, a
        game) changes what 3. Bindings and 4. Diagrams show, so their statuses
        in the strip are refreshed too, not only when they are opened."""
        if index in (STAGE_SETUP, STAGE_CONTROLLERS) and not self._cross_refreshing:
            self._cross_refreshing = True
            try:
                for later in (STAGE_BINDINGS, STAGE_DIAGRAMS):
                    page = self._pages[later]
                    if page is not None and later != self._current_stage:
                        self._safe_call(page, "refresh")
            finally:
                self._cross_refreshing = False
        self.refresh_strip()

    def _invalidate_data_pages(self) -> None:
        """Refresh the live pages in place (nothing is destroyed on a re-read)."""
        for index, page in enumerate(self._pages):
            if page is None or index == STAGE_SETUP:
                continue
            self._safe_call(page, "refresh")
        self.refresh_strip()

    # ── Banner slot ──

    def show_banner(
        self,
        text: str,
        actions: Iterable[tuple[str, Callable[[], None]]] = (),
        tone: str = "info",
        detail: str | None = None,
        key: str | None = None,
        on_dismiss: Callable[[], None] | None = None,
    ) -> QFrame:
        return self.banner.show_banner(
            text, actions, tone=tone, detail=detail, key=key, on_dismiss=on_dismiss
        )

    def clear_banner(self, key: str | None = None) -> None:
        self.banner.clear_banner(key)

    # ── Status bar ──

    def set_status_text(self, text: str, progress: int | None = None) -> None:
        """Status-bar text; ``progress`` 0–100 fills the bar, ``-1`` is busy,
        ``None`` leaves the bar empty."""
        self._status_text = text
        self.statusLabel.setText(text)
        if progress is None:
            self.progressBar.setRange(0, 100)
            self.progressBar.setValue(0)
        elif progress < 0:
            self.progressBar.setRange(0, 0)
        else:
            self.progressBar.setRange(0, 100)
            self.progressBar.setValue(max(0, min(100, progress)))

    # ── Background read ──

    @property
    def read_in_progress(self) -> bool:
        return self.reader.in_progress

    def start_read(self, wrappers: Iterable[Any] | None = None) -> bool:
        """Read the games in the background; ``False`` if nothing could start."""
        if wrappers is not None and not isinstance(wrappers, (list, tuple)):
            wrappers = None  # a bare ``clicked`` signal argument
        return self.reader.start(wrappers)

    def _on_read_started(self, games: list[str]) -> None:
        text = (
            S.STATUS_READING_GAME.format(game=games[0])
            if len(games) == 1
            else S.STATUS_READING_GAMES
        )
        self.set_status_text(text, progress=-1)
        self.clear_banner(BANNER_KEY_READ_FAILED)
        for page in self.pages:
            self._safe_call(page, "on_read_started", games)
        self.refresh_strip()
        self.read_started.emit(games)
        if self._launch_read:
            self._launch_read = False
            # Explain the automatic read once; after that the tab status and the
            # status bar are enough, and the popover opens on demand.
            if not workflow_settings.get_read_popover_shown():
                workflow_settings.set_read_popover_shown(True)
                self.show_read_popover(text)
        elif self.read_popover.isVisible():
            self.read_popover.set_reading(text)

    def show_read_popover(self, reading_text: str | None = None) -> None:
        """Open the read popover under the 1. Setup tab (first launch read, or
        when the user clicks that tab's status)."""
        self._popover_timer.stop()
        self.read_popover.set_automatic(workflow_settings.get_auto_read_on_launch())
        if reading_text is not None:
            self.read_popover.set_reading(reading_text)
        else:
            self.read_popover.set_idle(
                S.READ_POPOVER_UP_TO_DATE.format(time=self._last_read_time_text())
            )
        self.read_popover.show_under(self.strip.tab(STAGE_SETUP))

    def _last_read_time_text(self) -> str:
        return self._last_read_time or now_time_text()

    def _on_read_finished(self, outcome: ReadOutcome) -> None:
        self._last_read_time = outcome.finished_at or now_time_text()
        self.set_status_text(S.STATUS_APP_UP_TO_DATE)
        for page in self.pages:
            self._safe_call(page, "on_read_finished", outcome)
        self._invalidate_data_pages()
        if outcome.failed:
            self._show_read_failed_banner(outcome)
        self._show_new_controller_banners(outcome)
        if self.read_popover.isVisible():
            if outcome.ok:
                self.read_popover.set_idle(
                    S.READ_POPOVER_UP_TO_DATE.format(
                        time=outcome.finished_at or now_time_text()
                    )
                )
            else:
                game = next(iter(outcome.failed))
                self.read_popover.set_idle(
                    S.BANNER_READ_FAILED.format(game=game), ok=False
                )
            self._popover_timer.start(POPOVER_HIDE_DELAY_MS)
        self.read_finished.emit(outcome)

    def _show_read_failed_banner(self, outcome: ReadOutcome) -> None:
        games = list(outcome.failed)
        text = (
            S.BANNER_READ_FAILED.format(game=games[0])
            if len(games) == 1
            else S.BANNER_READ_FAILED_MANY.format(games=", ".join(games))
        )
        first = games[0]
        self.show_banner(
            text,
            [
                (
                    S.BANNER_CHOOSE_FOLDER,
                    lambda: self.go_to_stage(
                        STAGE_SETUP, {"game": first, "action": "choose_folder"}
                    ),
                ),
                (S.READ_AGAIN, self.start_read),
            ],
            tone="warning",
            key=BANNER_KEY_READ_FAILED,
        )

    def _show_new_controller_banners(self, outcome: ReadOutcome) -> None:
        new_guids = outcome.arrived_guids
        if not new_guids:
            return
        from joystick_diagrams.device_status import DeviceStatus, all_device_statuses

        dismissed = dismissed_new_controllers()
        try:
            statuses = all_device_statuses(
                self.appState.profile_wrappers, include_unseen=False
            )
        except Exception as error:  # noqa: BLE001 - notices are a courtesy
            _logger.debug(f"Could not compute statuses for new controllers: {error}")
            return
        for guid in new_guids:
            info = statuses.get(guid)
            if info is None or guid in dismissed:
                continue
            if info.state is not DeviceStatus.NEEDS_TEMPLATE:
                continue  # already drawn, merged or set to No diagram: nothing to ask
            name = info.name or guid
            games = sorted(info.games.items(), key=lambda item: -item[1])
            profiles = S.plural(info.profile_count, *S.PROFILES)
            detail = (
                S.BANNER_NEW_CONTROLLER_DETAIL.format(
                    game=games[0][0], count=info.profile_count, profiles=profiles
                )
                if games
                else S.BANNER_NEW_CONTROLLER_DETAIL_NO_GAME.format(
                    count=info.profile_count, profiles=profiles
                )
            )
            key = f"new-controller:{guid}"
            self.show_banner(
                S.BANNER_NEW_CONTROLLER.format(name=name),
                [
                    (
                        S.BANNER_CHOOSE_TEMPLATE,
                        lambda g=guid, k=key: self._choose_template_from_banner(g, k),
                    ),
                    (
                        S.BANNER_NO_DIAGRAM_NEEDED,
                        lambda g=guid, n=name, k=key: self._no_diagram_from_banner(
                            g, n, k
                        ),
                    ),
                ],
                detail=detail,
                key=key,
                on_dismiss=lambda g=guid: dismiss_new_controller(g),
            )

    def _choose_template_from_banner(self, guid: str, key: str) -> None:
        dismiss_new_controller(guid)
        self.clear_banner(key)
        self.choose_template_for(guid)

    def _no_diagram_from_banner(self, guid: str, name: str, key: str) -> None:
        self.appState.device_service.set_make_diagram(guid, False, name)
        dismiss_new_controller(guid)
        self.clear_banner(key)
        self._invalidate_data_pages()

    def _launch_auto_read(self) -> None:
        if (
            not self._auto_read_allowed
            or not workflow_settings.get_auto_read_on_launch()
        ):
            return
        if not self.games_set_up():
            return
        self._launch_read = True
        if not self.start_read():
            self._launch_read = False

    # ── Qt events ──

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        if self._shown_once:
            return
        self._shown_once = True
        QTimer.singleShot(0, self._after_first_show)

    def _after_first_show(self) -> None:
        if self._check_updates:
            self.check_for_new_version()
        self._launch_auto_read()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.read_popover.hide()
        for page in self.pages:
            self._safe_call(page, "shutdown")
        super().closeEvent(event)

    # ── Help menu actions ──

    def _open_discord(self):
        QDesktopServices.openUrl("https://discord.gg/UUyRUuX2dX")

    def _open_website(self):
        QDesktopServices.openUrl("https://joystick-diagrams.com")

    def _open_github(self):
        QDesktopServices.openUrl("https://github.com/Rexeh/joystick-diagrams")

    def _open_buymeacoffee(self):
        QDesktopServices.openUrl(
            "https://www.paypal.com/cgi-bin/webscr"
            "?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url"
        )

    def _open_logs_folder(self):
        log_path = data_root() / "logs"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))

    def _toggle_debug_mode(self, checked):
        logging.getLogger().setLevel(logging.DEBUG if checked else logging.INFO)

    def _check_for_updates(self):
        version_check = version.perform_version_check()
        if version_check is False:
            self.set_status_text(S.STATUS_UPDATE_AVAILABLE)
        elif version_check is True:
            self.set_status_text(S.STATUS_APP_UP_TO_DATE)
        else:
            self.set_status_text(S.STATUS_UPDATE_CHECK_FAILED)

    def _show_about(self):
        QMessageBox.about(
            self,
            S.ABOUT_TITLE,
            S.ABOUT_BODY.format(version=version.get_current_version()),
        )

    def check_for_new_version(self):
        _logger.info("Checking version...")
        self._check_for_updates()
        self._check_for_plugin_updates()

    def _check_for_plugin_updates(self):
        """Kick off a background game-list check and record when it ran."""
        from datetime import datetime, timezone

        from joystick_diagrams.db.db_settings import add_update_setting_value
        from joystick_diagrams.ui.setup_page import PLUGIN_CATALOG_LAST_CHECKED_KEY

        setup = self._pages[STAGE_SETUP]
        if setup is not None and hasattr(setup, "check_plugin_updates"):
            setup.check_plugin_updates()
            add_update_setting_value(
                PLUGIN_CATALOG_LAST_CHECKED_KEY, datetime.now(timezone.utc).isoformat()
            )

    # ── Helpers ──

    @staticmethod
    def _safe_call(target: Any, name: str, *args) -> Any:
        method = getattr(target, name, None)
        if not callable(method):
            return None
        try:
            return method(*args)
        except Exception as error:  # noqa: BLE001 - one page must not break the shell
            _logger.error(
                f"{type(target).__name__}.{name} failed: {error}", exc_info=True
            )
            return None


if __name__ == "__main__":
    pass
