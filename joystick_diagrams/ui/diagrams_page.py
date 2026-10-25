"""Stage 4, "4. Diagrams" (journey boards J08–J14).

A settings-style nav: **Export**, then under "Make changes" **Appearance**,
**Layout** and **Pages**. The stage lands on Export, every ready profile ticked.

- Export: ``ExportScreen`` (``ui/export_page.py``).
- Appearance: ``CustomiseAppearance`` (styles, modifier colours, Showing
  modifiers; a sample preview when no controller has a template).
- Layout: ``CustomiseLayout`` (the Diagram picker lists controllers, greyed
  ones that need a template, and pages); layouts are keyed by controller.
- Pages: ``PagesPage`` + the Combine dialog (``PagesDialog``).

Shell contract (``ui/stage_contract.py``): ``refresh()``; ``stage_status()`` →
("ok", "33 diagrams ready") / ("none", "Choose templates first") /
("busy", "Exporting 12 of 33…") / ("ok", "Exported 33 at 09:52") /
("warning", "Export stopped · no folder"); ``next_action()`` → the footer's
"Export N diagrams" on every sub-screen (it uses Export's ticks), "Export when
reading finishes" while the games are read; ``footer_hint()`` says the export
is queued; ``request_stage`` and ``navigate(payload)`` / ``handle_request`` for
deep links (``{"device_guid": …, "section": "layout"}`` opens Layout on that
controller; ``"section"`` one of export / appearance / layout / pages;
``"page_id"`` with layout opens a page).
"""

from __future__ import annotations

import logging

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.app_state import AppState
from joystick_diagrams.ui import strings_diagrams as S
from joystick_diagrams.ui.shell_access import find_shell
from joystick_diagrams.ui.stage_contract import (
    PAYLOAD_DEVICE_GUID,
    PAYLOAD_SECTION,
    SECTION_APPEARANCE,
    SECTION_EXPORT,
    SECTION_LAYOUT,
    SECTION_PAGES,
    STAGE_CONTROLLERS,
    NextAction,
    StageStatus,
)

_logger = logging.getLogger(__name__)

PAYLOAD_PAGE_ID = "page_id"
PAYLOAD_TAB = "tab"
SECTIONS = (SECTION_EXPORT, SECTION_APPEARANCE, SECTION_LAYOUT, SECTION_PAGES)
# Nav rows: Export, the "Make changes" heading, Appearance, Layout, Pages
NAV_ROWS = (SECTION_EXPORT, None, SECTION_APPEARANCE, SECTION_LAYOUT, SECTION_PAGES)
HEADING_STYLE = (
    "color: #6B7280; font-size: 10px; font-weight: bold; text-transform: uppercase;"
)


class DiagramsPage(QWidget):
    request_stage = Signal(int, dict)
    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.appState = AppState()
        self._screens: dict[str, QWidget] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setProperty("class", "settings-nav")
        self.nav_list.setAccessibleName(S.TITLE)
        for section in NAV_ROWS:
            if section is None:
                item = QListWidgetItem(S.NAV_MAKE_CHANGES)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setSizeHint(QSize(0, 30))
                item.setForeground(QColor("#9AA0A6"))
                font = item.font()
                font.setPixelSize(11)  # the app's floor for small labels
                font.setBold(True)
                item.setFont(font)
            else:
                icon, label = {
                    SECTION_EXPORT: ("fa5s.file-export", S.NAV_EXPORT),
                    SECTION_APPEARANCE: ("fa5s.palette", S.NAV_APPEARANCE),
                    SECTION_LAYOUT: ("fa5s.th-large", S.NAV_LAYOUT),
                    SECTION_PAGES: ("fa5s.object-group", S.NAV_PAGES),
                }[section]
                item = QListWidgetItem(qta.icon(icon, color="#9AA0A6"), label)
                item.setSizeHint(QSize(0, 44))
            self.nav_list.addItem(item)
        root.addWidget(self.nav_list)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.section_heading = QLabel()
        self.section_heading.setObjectName("heading_label")
        self.section_heading.setContentsMargins(20, 16, 20, 0)
        content_layout.addWidget(self.section_heading)
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        root.addWidget(content, 1)

        # A page edited in Layout updates the Export rows and the footer count
        # once the edits pause (a slider drag is many saves)
        self._page_edit_timer = QTimer(self)
        self._page_edit_timer.setSingleShot(True)
        self._page_edit_timer.setInterval(400)
        self._page_edit_timer.timeout.connect(self._on_page_edited_in_layout)

        from joystick_diagrams.ui.export_page import ExportScreen

        self.export_screen = ExportScreen()
        # Scrolls instead of squashing the list when the window is short
        self.export_scroll = QScrollArea()
        self.export_scroll.setWidgetResizable(True)
        self.export_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.export_scroll.setWidget(self.export_screen)
        self._screens[SECTION_EXPORT] = self.export_screen
        self.stack.addWidget(self.export_scroll)
        self.export_screen.state_changed.connect(self.state_changed.emit)
        self.export_screen.request_stage.connect(self.request_stage.emit)
        self.export_screen.appearance_requested.connect(
            lambda: self.show_section(SECTION_APPEARANCE)
        )
        self.export_screen.layout_requested.connect(self.show_layout)
        self.export_screen.page_layout_requested.connect(self.show_page_layout)
        self.export_screen.combine_requested.connect(self.combine)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)

    # ── Screens (built on first use: Appearance and Layout start WebEngine views) ──

    def _add_screen(self, section: str, widget: QWidget) -> None:
        self._screens[section] = widget
        self.stack.addWidget(widget)

    def screen(self, section: str) -> QWidget:
        widget = self._screens.get(section)
        if widget is not None:
            return widget
        if section == SECTION_APPEARANCE:
            from joystick_diagrams.ui.customise_appearance import CustomiseAppearance

            widget = CustomiseAppearance()
        elif section == SECTION_LAYOUT:
            from joystick_diagrams.ui.customise_layout import CustomiseLayout

            widget = CustomiseLayout()
            widget.devices_changed.connect(self._on_controllers_changed)
            widget.go_to_controllers_requested.connect(
                lambda: self.request_stage.emit(STAGE_CONTROLLERS, {})
            )
            widget.pages_changed.connect(self._page_edit_timer.start)
        elif section == SECTION_PAGES:
            from joystick_diagrams.ui.pages_page import PagesPage

            widget = PagesPage()
            widget.pages_changed.connect(self._on_pages_changed)
            widget.page_created.connect(self._on_page_created)
            widget.layout_requested.connect(self.show_page_layout)
        else:
            return self.export_screen
        self._add_screen(section, widget)
        return widget

    @property
    def appearance_screen(self) -> QWidget:
        return self.screen(SECTION_APPEARANCE)

    @property
    def layout_screen(self) -> QWidget:
        return self.screen(SECTION_LAYOUT)

    @property
    def pages_screen(self) -> QWidget:
        return self.screen(SECTION_PAGES)

    def current_section(self) -> str:
        return NAV_ROWS[self.nav_list.currentRow()] or SECTION_EXPORT

    def show_section(self, section: str) -> None:
        if section in SECTIONS:
            self.nav_list.setCurrentRow(NAV_ROWS.index(section))

    def _on_nav_changed(self, row: int) -> None:
        if row < 0 or NAV_ROWS[row] is None:
            return
        section = NAV_ROWS[row]
        widget = self.screen(section)
        self.stack.setCurrentWidget(
            self.export_scroll if widget is self.export_screen else widget
        )
        titles = {
            SECTION_APPEARANCE: S.NAV_APPEARANCE,
            SECTION_LAYOUT: S.NAV_LAYOUT,
        }
        title = titles.get(section)
        self.section_heading.setVisible(title is not None)
        self.section_heading.setText(title or "")
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()
        self.state_changed.emit()

    # ── Shell contract ──

    def refresh(self) -> None:
        self.export_screen.refresh()
        current = self.stack.currentWidget()
        if current is not self.export_scroll:
            refresh = getattr(current, "refresh", None)
            if callable(refresh):
                refresh()

    def stage_status(self) -> StageStatus:
        screen = self.export_screen
        if not screen.loaded:
            screen.refresh()
        if screen.is_exporting:
            done, total = screen.progress
            return StageStatus(
                "busy", S.STATUS_EXPORTING.format(done=done, total=total)
            )
        if screen.stopped_reason:
            return StageStatus(
                "warning", S.STATUS_EXPORT_STOPPED.format(reason=screen.stopped_reason)
            )
        if screen.queued:
            return StageStatus("busy", S.STATUS_QUEUED)
        if not screen.ready_count():
            if screen.read_in_progress():
                return StageStatus("busy", S.STATUS_WAITING_FOR_READ)
            if screen.waiting_count():
                return StageStatus("none", S.STATUS_CHOOSE_TEMPLATES)
            return StageStatus("none", S.STATUS_NOTHING_TO_EXPORT)
        count = screen.export_count()
        last = screen.last_export
        if last is not None and last[0] == count and count:
            return StageStatus(
                "ok", S.STATUS_EXPORTED_AT.format(count=count, time=last[1])
            )
        if not count:
            return StageStatus("none", S.EXPORT_DISABLED_TIP)
        return StageStatus(
            "ok",
            S.STATUS_READY.format(count=count, diagrams=S.plural(count, *S.DIAGRAMS)),
        )

    def next_action(self) -> NextAction | None:
        screen = self.export_screen
        if not screen.loaded:
            screen.refresh()
        if screen.is_exporting:
            return NextAction(S.EXPORT_RUNNING, lambda: None, enabled=False)
        count = screen.export_count()
        if screen.read_in_progress() and screen.can_queue():
            return NextAction(
                S.EXPORT_WHEN_READ_FINISHES,
                screen.queue_export,
                enabled=not screen.queued,
                tooltip=S.EXPORT_QUEUED_HINT,
            )
        if not count:
            return NextAction(
                S.EXPORT_DISABLED,
                lambda: None,
                enabled=False,
                tooltip=S.EXPORT_DISABLED_TIP,
            )
        return NextAction(
            S.EXPORT_N.format(count=count, diagrams=S.plural(count, *S.DIAGRAMS)),
            self.export,
        )

    def footer_hint(self) -> str | None:
        if self.export_screen.queued:
            return S.EXPORT_QUEUED_HINT
        return None

    def export(self) -> None:
        """The footer button: export what Export has ticked, from any sub-screen."""
        self.export_screen.start_export()

    def on_read_started(self, *args) -> None:
        self.export_screen.on_read_started(*args)
        self.state_changed.emit()

    def on_read_finished(self, *args) -> None:
        self.export_screen.on_read_finished(*args)
        self.state_changed.emit()

    def navigate(self, payload: dict) -> None:
        payload = payload or {}
        section = payload.get(PAYLOAD_SECTION) or SECTION_EXPORT
        guid = payload.get(PAYLOAD_DEVICE_GUID)
        page_id = payload.get(PAYLOAD_PAGE_ID)
        if section == SECTION_LAYOUT:
            if page_id:
                self.show_page_layout(page_id)
            else:
                self.show_layout(guid)
            return
        self.show_section(section)
        if section == SECTION_APPEARANCE and payload.get(PAYLOAD_TAB) is not None:
            self.appearance_screen.show_tab(int(payload[PAYLOAD_TAB]))
        if section == SECTION_PAGES and page_id:
            self.pages_screen.select_page(page_id)

    handle_request = navigate

    def shutdown(self) -> None:
        self.export_screen.shutdown()
        layout = self._screens.get(SECTION_LAYOUT)
        if layout is not None:
            layout.shutdown()
        appearance = self._screens.get(SECTION_APPEARANCE)
        preview = getattr(getattr(appearance, "style_tab", None), "preview", None)
        if preview is not None:
            preview.shutdown()

    # ── Deep links between sub-screens ──

    def show_appearance(self, tab: int | None = None) -> None:
        self.show_section(SECTION_APPEARANCE)
        if tab is not None:
            self.appearance_screen.show_tab(tab)

    def show_layout(self, device_id: str | None = None) -> None:
        self.show_section(SECTION_LAYOUT)
        self.layout_screen.show_device(device_id)

    def show_page_layout(self, page_id: str) -> None:
        self.show_section(SECTION_LAYOUT)
        self.layout_screen.show_page(page_id)

    def combine(self) -> None:
        """Export › Combine onto one page…: the dialog, then back to Export."""
        from joystick_diagrams.ui.pages_dialog import PagesDialog

        screen = self.export_screen
        dialog = PagesDialog(
            self, statuses=screen._statuses, export_devices=screen._export_devices
        )
        if dialog.exec() != PagesDialog.DialogCode.Accepted or dialog.page is None:
            return
        self._on_page_created(dialog.page.page_id)

    def _on_page_created(self, page_id: str) -> None:
        """Back to Export with the page ticked, and the banner pointing at Layout."""
        self._on_pages_changed()
        self.show_section(SECTION_EXPORT)
        self.export_screen.tick_page(page_id)
        shell = find_shell(self)
        if shell is not None and hasattr(shell, "show_banner"):
            try:
                shell.show_banner(
                    S.PAGE_CREATED_BANNER,
                    [(S.PAGE_CREATED_ACTION, lambda: self.show_page_layout(page_id))],
                )
            except Exception as error:  # noqa: BLE001 - a courtesy only
                _logger.debug(f"Banner not shown: {error}")
        self.state_changed.emit()

    def _on_pages_changed(self) -> None:
        self.export_screen.refresh()
        layout = self._screens.get(SECTION_LAYOUT)
        if layout is not None:
            layout._signature = None
        self.state_changed.emit()

    def _on_page_edited_in_layout(self) -> None:
        self.export_screen.refresh()
        self.state_changed.emit()

    def _on_controllers_changed(self) -> None:
        self.export_screen.refresh()
        shell = find_shell(self)
        refresh_strip = getattr(shell, "refresh_strip", None)
        if callable(refresh_strip):
            refresh_strip()
        self.state_changed.emit()


if __name__ == "__main__":
    pass
