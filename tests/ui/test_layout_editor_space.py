"""4. Diagrams › Layout gets the space (docs/superpowers/specs/2026-11-01-layout-editor-space.md):
the icon rail, the scope dropdown, the drawer on a narrow window, nothing cut
off at 800x600, fit to width on first open and undo kept per diagram."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, Qt  # noqa: E402
from PySide6.QtWidgets import QAbstractScrollArea, QLayout, QWidget  # noqa: E402

from joystick_diagrams.render.layout import TEMPLATE_LAYER  # noqa: E402
from joystick_diagrams.ui import customise_layout  # noqa: E402
from joystick_diagrams.ui import strings_diagrams as D  # noqa: E402
from joystick_diagrams.ui import strings_layout as S  # noqa: E402
from joystick_diagrams.ui.customise_layout import (  # noqa: E402
    DRAWER_WIDTH,
    PANEL_WIDTH,
    ZOOM_FIT_WIDTH,
    CustomiseLayout,
)
from joystick_diagrams.ui.diagrams_page import (  # noqa: E402
    NAV_WIDTH,
    RAIL_WIDTH,
    DiagramsPage,
)
from joystick_diagrams.ui.stage_contract import (  # noqa: E402
    SECTION_APPEARANCE,
    SECTION_EXPORT,
    SECTION_LAYOUT,
    SECTION_PAGES,
)
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    STICK,
    THROTTLE,
    FakeShell,
    _reset_app_state,
    seed_state,
    settings_store,
)


def _settle(*widgets: QWidget) -> None:
    for _ in range(5):
        for widget in widgets:
            widget.layout().activate()
        QCoreApplication.processEvents()


def _unconstrained(widget: QWidget) -> QWidget:
    """A top-level test widget may be resized below its layout's minimum, as it
    is inside the window (the window's own minimum is 800x600)."""
    widget.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
    return widget


@pytest.fixture
def screen(qapp, settings_store):
    seed_state()
    screen = CustomiseLayout()
    screen.refresh()
    screen.render_synchronously()
    yield screen
    screen.shutdown()


def _move(screen, target="button_1#1", dx=10):
    screen.bridge.applyGesture(
        json.dumps({"gesture": "move", "target": target, "dx": dx, "dy": 0})
    )


def _clipped(root: QWidget) -> list[str]:
    """Visible widgets that stick out of their parent (scrolled content aside)."""
    problems = []
    for child in root.findChildren(QWidget):
        parent = child.parentWidget()
        if (
            not child.isVisible()
            or child.isWindow()
            or parent is None
            or isinstance(parent.parentWidget(), QAbstractScrollArea)
        ):
            continue
        if not parent.rect().contains(child.geometry()):
            problems.append(
                f"{type(child).__name__} {child.geometry()} in {parent.rect()}"
            )
    return problems


# ── 1. The rail ──


@pytest.mark.uitest
def test_rail_shows_only_while_layout_is_open(qapp, settings_store):
    seed_state()
    shell = FakeShell()
    page = DiagramsPage(shell)
    page.refresh()
    assert not page.rail_shown and page.nav_stack.width() == NAV_WIDTH
    page.show_section(SECTION_LAYOUT)
    assert page.rail_shown and page.nav_stack.maximumWidth() == RAIL_WIDTH
    assert page.rail_buttons[SECTION_LAYOUT].isChecked()
    assert not page.section_heading.isVisibleTo(page)  # Layout has its own
    labels = {
        SECTION_EXPORT: D.NAV_EXPORT,
        SECTION_APPEARANCE: D.NAV_APPEARANCE,
        SECTION_LAYOUT: D.NAV_LAYOUT,
        SECTION_PAGES: D.NAV_PAGES,
    }
    for section, label in labels.items():
        button = page.rail_buttons[section]
        assert button.toolTip() == label and button.accessibleName() == label
    page.rail_buttons[SECTION_PAGES].click()
    assert page.current_section() == SECTION_PAGES
    assert not page.rail_shown and page.nav_stack.maximumWidth() == NAV_WIDTH
    page.shutdown()


# ── 2. Scope dropdown and the help line ──


@pytest.mark.uitest
def test_scope_dropdown_and_help_line_goes_after_the_first_edit(screen, settings_store):
    combo = screen.scope_combo
    assert combo.itemText(0) == S.SCOPE_ALL_PROFILES
    assert combo.itemText(1) == "Only F-16C"
    assert screen.scope_layer == TEMPLATE_LAYER
    combo.setCurrentIndex(1)
    assert screen.scope_layer == "dcs world_f-16c"
    assert settings_store["layout_editor_last_scope"] == "profile"
    combo.setCurrentIndex(0)
    assert screen.scope_layer == TEMPLATE_LAYER

    assert screen.help_label.isVisibleTo(screen)
    _move(screen)
    assert not screen.help_label.isVisibleTo(screen)
    screen.show_device(THROTTLE)  # stays hidden for the visit
    assert not screen.help_label.isVisibleTo(screen)


# ── 3. Drawer on a narrow screen; nothing cut off at 800x600 ──


@pytest.mark.uitest
def test_panel_is_a_drawer_below_the_threshold(screen):
    _unconstrained(screen)
    screen.resize(1400, 800)
    screen.show()
    _settle()
    assert not screen.drawer_mode
    assert screen.panel_stack.parentWidget() is screen
    assert screen.panel_stack.width() == PANEL_WIDTH
    assert screen.spin_y.parentWidget() is not None
    grid = screen._xywh_grid
    assert grid.getItemPosition(grid.indexOf(screen.spin_h))[:2] == (1, 3)

    screen.resize(900, 700)
    _settle()
    assert screen.drawer_mode
    assert screen.panel_stack.parentWidget() is screen.drawer
    assert screen.drawer.parentWidget() is screen.canvas_stack_widget
    assert not screen.drawer.isVisible()  # nothing selected: the canvas is whole
    screen._on_selection_changed("button_1#1")
    _settle()
    assert screen.drawer.isVisible()
    host = screen.canvas_stack_widget.rect()
    assert screen.drawer.geometry().width() == DRAWER_WIDTH
    assert screen.drawer.geometry().right() == host.right()
    assert screen.drawer.geometry().height() == host.height()
    # X/Y/W/H stack 2x2 in the drawer
    assert grid.getItemPosition(grid.indexOf(screen.spin_h))[:2] == (3, 1)
    screen._on_selection_changed("")
    assert not screen.drawer.isVisible()

    screen.resize(1400, 800)
    _settle()
    assert not screen.drawer_mode and screen.panel_stack.isVisible()
    assert screen.panel_stack.parentWidget() is screen


@pytest.mark.uitest
def test_nothing_is_cut_off_at_the_minimum_window(qapp, settings_store):
    """800x600 leaves the Diagrams stage about 800x403 under the strip and footer."""
    state = seed_state()
    page_obj = state.page_service.create("Stick + Throttle", [STICK, THROTTLE])
    page = _unconstrained(DiagramsPage())  # top-level: shown for real
    page.resize(800, 403)
    page.show()
    page.show_layout(STICK)
    layout = page.layout_screen
    layout.render_synchronously()
    layout._on_selection_changed("button_1#1")
    _settle(page, layout)
    assert layout.width() == 800 - RAIL_WIDTH
    assert layout.drawer_mode and layout.drawer.isVisible()
    assert layout.minimumSizeHint().width() <= layout.width()
    assert layout.minimumSizeHint().height() <= layout.height()
    canvas = layout.canvas_stack_widget
    assert canvas.width() >= 320 and canvas.height() >= 240
    assert _clipped(page) == []

    layout.show_page(page_obj.page_id)  # the page panel in the drawer
    _settle(page, layout)
    assert layout.drawer.isVisible()
    assert layout.panel_stack.currentWidget() is layout.page_panel_scroll
    assert _clipped(page) == []
    page.shutdown()


# ── 4. Fit to width on first open, zoom per diagram ──


@pytest.mark.uitest
def test_first_showing_fits_the_width_and_zoom_is_kept_per_diagram(
    screen, settings_store
):
    screen.show_device(STICK)
    render = screen.render_synchronously()
    assert screen._document_payload(render)["zoom"] == ZOOM_FIT_WIDTH
    assert "zoom" not in screen._document_payload(render)  # re-render: keep zoom
    screen.bridge.zoomChanged(80)
    screen._save_zoom()
    assert settings_store[customise_layout.LAYOUT_EDITOR_ZOOM_SETTING_KEY] == "0.8"

    screen.show_device(THROTTLE)
    render = screen.render_synchronously()
    assert screen._document_payload(render)["zoom"] == ZOOM_FIT_WIDTH
    screen.bridge.zoomChanged(150)

    screen.show_device(STICK)
    render = screen.render_synchronously()
    assert screen._document_payload(render)["zoom"] == 0.8
    assert screen.diagram_zooms == {STICK: 0.8, THROTTLE: 1.5}


# ── 5. Undo per diagram for the visit ──


@pytest.mark.uitest
def test_undo_survives_switching_diagrams_and_refreshes(screen):
    screen.show_device(STICK)
    screen.render_synchronously()
    _move(screen)
    stick_session = screen._session
    assert stick_session.can_undo

    screen.show_device(THROTTLE)
    screen.render_synchronously()
    assert screen._session is not stick_session
    assert not screen.undo_button.isEnabled()

    screen.show_device(STICK)
    screen.render_synchronously()
    assert screen._session is stick_session
    assert screen.undo_button.isEnabled()

    # A forced re-read of the lists (pages changed, games read) keeps it too
    screen._signature = None
    screen.refresh()
    assert screen._session is stick_session
    screen.undo()
    assert stick_session.ops_in(TEMPLATE_LAYER) == []


@pytest.mark.uitest
def test_a_new_template_starts_a_new_history(screen):
    screen.show_device(STICK)
    screen.render_synchronously()
    _move(screen)
    old = screen._session
    entry = screen.current_diagram()
    old.content_hash = "bytes from before the template file changed"
    screen._on_diagram_changed()
    assert screen._session is not old and not screen._session.can_undo
    assert screen._session.device_guid == entry.device_id


def test_undo_strings_say_what_is_true():
    for text in (S.PANEL_UNDO_NOTE, S.RESET_ALL_TEXT, S.PAGE_PANEL_UNDO_NOTE):
        assert "leave this screen" not in text and "stay on this screen" not in text
        assert "close the app" in text
    assert "this diagram" in S.PANEL_UNDO_NOTE
    assert "this page" in S.PAGE_PANEL_UNDO_NOTE
    assert "already saved" in S.PANEL_UNDO_NOTE


@pytest.mark.uitest
def test_compact_toolbar_keeps_names_for_icon_only_tools(screen):
    screen.show()
    screen._set_compact_tools(True)  # what a narrow window with the app's style gets
    assert (
        screen.select_button.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
    )
    for button in screen._icon_tools:
        assert button.accessibleName() and button.toolTip()
    assert screen.zoom_menu_button.isVisible() and not screen.fit_button.isVisible()
