"""The main window remembers its size, position and maximised state between
launches (``workflow_settings.window_geometry``)."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QRect, Qt, Signal  # noqa: E402
from PySide6.QtWidgets import QWidget  # noqa: E402

from joystick_diagrams import workflow_settings  # noqa: E402
from joystick_diagrams.ui.stage_contract import StageStatus  # noqa: E402
from joystick_diagrams.workflow_settings import (  # noqa: E402
    WINDOW_GEOMETRY_SETTING_KEY,
    WindowGeometry,
)
from tests.ui.stage_fixtures import (  # noqa: E402
    drain,
    patched_settings,
    seed_app_state,
)


class FakePage(QWidget):
    request_stage = Signal(int, dict)

    def __init__(self, index):
        super().__init__()
        self.status = StageStatus("none", f"Stage {index}")

    def refresh(self):
        pass

    def stage_status(self):
        return self.status

    def next_action(self):
        return None

    def secondary_action(self):
        return None

    def footer_hint(self):
        return None

    def handle_request(self, payload):
        pass


@pytest.fixture
def store(temp_database):
    with patched_settings() as settings:
        seed_app_state()
        yield settings
    drain()
    from joystick_diagrams.app_state import AppState

    AppState._inst = None


def make_window(qtbot):
    from joystick_diagrams.ui.main_window import MainWindow

    pages = [FakePage(i) for i in range(4)]
    window = MainWindow(
        page_factories={i: (lambda p=p: p) for i, p in enumerate(pages)},
        auto_read=False,
        check_updates=False,
    )
    qtbot.addWidget(window)
    return window


def saved(store):
    return json.loads(store[WINDOW_GEOMETRY_SETTING_KEY])


# ── The settings helper ──


def test_geometry_round_trips(store):
    workflow_settings.set_window_geometry(WindowGeometry(10, -20, 900, 700, True))
    assert saved(store) == {"x": 10, "y": -20, "w": 900, "h": 700, "maximized": True}
    assert workflow_settings.get_window_geometry() == WindowGeometry(
        10, -20, 900, 700, True
    )


def test_missing_geometry_is_none(store):
    assert workflow_settings.get_window_geometry() is None
    store[WINDOW_GEOMETRY_SETTING_KEY] = "  "
    assert workflow_settings.get_window_geometry() is None


@pytest.mark.parametrize(
    "raw",
    [
        "not json {",
        "[1, 2, 3, 4]",
        '{"x": 0, "y": 0, "w": 900}',
        '{"x": "0", "y": 0, "w": 900, "h": 700}',
        '{"x": 0, "y": 0, "w": 0, "h": 700}',
        '{"x": 0, "y": 0, "w": 900, "h": -1}',
        '{"x": true, "y": 0, "w": 900, "h": 700}',
        '{"x": 0.5, "y": 0, "w": 900, "h": 700}',
    ],
)
def test_invalid_geometry_is_none(store, raw):
    store[WINDOW_GEOMETRY_SETTING_KEY] = raw
    assert workflow_settings.get_window_geometry() is None


def test_maximized_defaults_to_false(store):
    store[WINDOW_GEOMETRY_SETTING_KEY] = '{"x": 1, "y": 2, "w": 900, "h": 700}'
    assert workflow_settings.get_window_geometry() == WindowGeometry(1, 2, 900, 700)


# ── Restoring at launch ──


def test_no_saved_geometry_keeps_the_default_size(qtbot, store):
    window = make_window(qtbot)
    assert (window.width(), window.height()) == (1100, 900)
    assert not window.windowState() & Qt.WindowState.WindowMaximized


def test_restore_applies_a_saved_rect_on_a_screen(qtbot, store):
    workflow_settings.set_window_geometry(WindowGeometry(20, 30, 900, 700))
    window = make_window(qtbot)
    assert window.geometry() == QRect(20, 30, 900, 700)
    assert not window.windowState() & Qt.WindowState.WindowMaximized


def test_restore_ignores_a_rect_off_every_screen(qtbot, store):
    workflow_settings.set_window_geometry(WindowGeometry(50_000, 50_000, 900, 700))
    window = make_window(qtbot)
    assert (window.width(), window.height()) == (1100, 900)
    assert window.x() < 50_000


def test_restore_never_goes_below_the_minimum_size(qtbot, store):
    workflow_settings.set_window_geometry(WindowGeometry(20, 30, 300, 200))
    window = make_window(qtbot)
    assert window.geometry() == QRect(20, 30, 800, 600)


def test_restore_maximises_when_saved_maximised(qtbot, store):
    workflow_settings.set_window_geometry(WindowGeometry(20, 30, 900, 700, True))
    window = make_window(qtbot)
    assert window.windowState() & Qt.WindowState.WindowMaximized
    window.show()
    qtbot.waitExposed(window)
    assert window.isMaximized()
    assert window.normalGeometry() == QRect(20, 30, 900, 700)


# ── Saving on close ──


def test_close_saves_the_normal_geometry(qtbot, store):
    window = make_window(qtbot)
    window.show()
    qtbot.waitExposed(window)
    window.setGeometry(QRect(40, 50, 850, 650))
    window.close()
    assert saved(store) == {"x": 40, "y": 50, "w": 850, "h": 650, "maximized": False}


def test_close_when_maximised_saves_the_normal_geometry(qtbot, store):
    window = make_window(qtbot)
    window.setGeometry(QRect(40, 50, 850, 650))
    window.show()
    qtbot.waitExposed(window)
    window.showMaximized()
    qtbot.waitUntil(window.isMaximized)
    window.close()
    assert saved(store) == {"x": 40, "y": 50, "w": 850, "h": 650, "maximized": True}


def test_saved_geometry_is_restored_by_the_next_window(qtbot, store):
    first = make_window(qtbot)
    first.show()
    qtbot.waitExposed(first)
    first.setGeometry(QRect(60, 70, 820, 610))
    first.close()
    second = make_window(qtbot)
    assert second.geometry() == QRect(60, 70, 820, 610)
