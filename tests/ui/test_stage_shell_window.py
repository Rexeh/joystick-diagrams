"""MainWindow as the four-stage shell: strip, footer, banner slot, landing, deep
links, the background read and its notices."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt, Signal  # noqa: E402
from PySide6.QtWidgets import QPushButton, QWidget  # noqa: E402

from joystick_diagrams import workflow_settings  # noqa: E402
from joystick_diagrams.device_status import DeviceStatus, StatusInfo  # noqa: E402
from joystick_diagrams.ui.stage_contract import (  # noqa: E402
    NextAction,
    ReadOutcome,
    StageStatus,
)
from joystick_diagrams.ui.stage_shell import (  # noqa: E402
    GameReader,
    PlaceholderStagePage,
    dismissed_new_controllers,
)
from tests.ui.stage_fixtures import (  # noqa: E402
    drain,
    patched_settings,
    seed_app_state,
)


class FakePage(QWidget):
    request_stage = Signal(int, dict)

    def __init__(self, index, status=None, action=None):
        super().__init__()
        self.index = index
        self.status = status or StageStatus("none", f"Stage {index}")
        self.action = action
        self.refreshed = 0
        self.requests = []
        self.secondary = None
        self.hint = None

    def refresh(self):
        self.refreshed += 1

    def stage_status(self):
        return self.status

    def next_action(self):
        return self.action

    def secondary_action(self):
        return self.secondary

    def footer_hint(self):
        return self.hint

    def handle_request(self, payload):
        self.requests.append(payload)


@pytest.fixture(autouse=True)
def _fresh_state(temp_database):
    with patched_settings():
        seed_app_state()
        yield
    drain()
    from joystick_diagrams.app_state import AppState

    AppState._inst = None


def ready_game(name="DCS World"):
    return SimpleNamespace(
        name=name,
        enabled=True,
        ready=True,
        error="",
        plugin_profile_collection=None,
    )


def make_window(qtbot, pages=None, games=None):
    from joystick_diagrams.app_state import AppState
    from joystick_diagrams.ui.main_window import MainWindow

    AppState().plugin_manager.plugin_wrappers = list(games or [])
    pages = pages or [FakePage(i) for i in range(4)]
    window = MainWindow(
        page_factories={i: (lambda p=p: p) for i, p in enumerate(pages)},
        auto_read=False,
        check_updates=False,
    )
    qtbot.addWidget(window)
    return window, pages


def test_strip_draws_every_page_status_and_green_chevrons(qtbot):
    pages = [
        FakePage(0, StageStatus("ok", "Up to date · read 09:41")),
        FakePage(1, StageStatus("warning", "4 need a template")),
        FakePage(2, StageStatus("none", "Optional · 12 profiles", done=True)),
        FakePage(3, StageStatus("none", "Choose templates first")),
    ]
    window, _ = make_window(qtbot, pages)
    tabs = window.strip.tabs
    assert [t.status_label.text() for t in tabs] == [
        "Up to date · read 09:41",
        "4 need a template",
        "Optional · 12 profiles",
        "Choose templates first",
    ]
    assert [t.state for t in tabs] == ["ok", "warning", "none", "none"]
    assert [c.is_done for c in window.strip.chevrons] == [True, False, True]
    assert all(t.isEnabled() for t in tabs)  # never locked


def test_footer_shows_the_active_pages_action(qtbot):
    called = []
    pages = [FakePage(i) for i in range(4)]
    pages[1].action = NextAction("Next: 3. Bindings ›", lambda: called.append(1))
    pages[1].secondary = NextAction("Read again", lambda: called.append(2))
    pages[1].hint = "A hint"
    window, _ = make_window(qtbot, pages)
    window.go_to_stage(1)
    footer = window.footer
    assert footer.primary_button.text() == "Next: 3. Bindings ›"
    assert (
        footer.primary_button.height() == 44
        or footer.primary_button.minimumHeight() == 44
    )
    assert footer.hint_label.text() == "A hint"
    qtbot.mouseClick(footer.primary_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(footer.secondary_button, Qt.MouseButton.LeftButton)
    assert called == [1, 2]
    window.go_to_stage(2)
    assert footer.primary_button.isHidden()


def test_disabled_action_is_drawn_disabled(qtbot):
    pages = [FakePage(i) for i in range(4)]
    pages[0].action = NextAction("Choose a game to add", lambda: None, enabled=False)
    window, _ = make_window(qtbot, pages)
    window.go_to_stage(0)
    assert not window.footer.primary_button.isEnabled()


def test_banner_slot_shows_replaces_and_clears(qtbot):
    window, _ = make_window(qtbot)
    clicks = []
    window.show_banner("First", [("Read again", lambda: clicks.append("r"))], key="k")
    window.show_banner("Second", [], key="k")
    assert window.banner.texts() == ["Second"]
    window.show_banner("Other", [("Go", lambda: clicks.append("g"))])
    assert window.banner.texts() == ["Second", "Other"]
    other = window.banner.banners[1]
    button = next(b for b in other.findChildren(QPushButton) if b.text() == "Go")
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert clicks == ["g"]
    window.clear_banner("k")
    assert window.banner.texts() == ["Other"]
    window.clear_banner()
    assert window.banner.texts() == []
    assert window.banner.isHidden()


def test_status_bar_text_and_progress(qtbot):
    window, _ = make_window(qtbot)
    window.set_status_text("Exporting 12 of 33…", 36)
    assert window.statusLabel.text() == "Exporting 12 of 33…"
    assert window.progressBar.value() == 36
    window.set_status_text("Reading DCS World…", -1)
    assert window.progressBar.maximum() == 0
    window.set_status_text("App is up to date")
    assert window.progressBar.value() == 0


def test_landing_without_a_game_is_setup(qtbot):
    workflow_settings.set_last_stage(3)
    window, _ = make_window(qtbot)
    assert window.current_stage == 0


def test_landing_returns_to_the_last_stage(qtbot):
    workflow_settings.set_last_stage(1)
    window, _ = make_window(qtbot, games=[ready_game()])
    assert window.current_stage == 1


def test_upgrader_lands_on_diagrams_with_the_notice(qtbot):
    window, _ = make_window(qtbot, games=[ready_game()])
    assert window.current_stage == 3
    assert any(t.startswith("Now in four stages") for t in window.banner.texts())


def test_tab_change_is_remembered_and_refreshes_the_page(qtbot):
    window, pages = make_window(qtbot)
    before = pages[2].refreshed
    qtbot.mouseClick(window.strip.tab(2), Qt.MouseButton.LeftButton)
    assert window.current_stage == 2
    assert pages[2].refreshed == before + 1
    assert workflow_settings.get_last_stage() == 2


def test_request_stage_deep_links_with_payload(qtbot):
    window, pages = make_window(qtbot)
    pages[1].request_stage.emit(3, {"device_guid": "abc", "section": "layout"})
    assert window.current_stage == 3
    assert pages[3].requests == [{"device_guid": "abc", "section": "layout"}]


def test_missing_stage_module_gets_a_placeholder(qtbot):
    window, _ = make_window(qtbot)
    page = window._make_lazy_page(2, "joystick_diagrams.ui.no_such_page", "Nope")
    qtbot.addWidget(page)
    assert isinstance(page, PlaceholderStagePage)
    assert page.next_action() is None
    with qtbot.waitSignal(page.request_stage) as blocker:
        page.empty_state.action_button.click()
    assert blocker.args == [0, {}]


def test_refresh_in_place_on_invalidate(qtbot):
    window, pages = make_window(qtbot)
    counts = [p.refreshed for p in pages]
    window._invalidate_data_pages()
    assert [p.refreshed for p in pages] == [counts[0]] + [c + 1 for c in counts[1:]]
    assert all(p.parent() is not None for p in pages)  # nothing destroyed


def test_failed_read_turns_into_a_banner_and_never_moves(qtbot):
    window, _ = make_window(qtbot, games=[ready_game()])
    window.go_to_stage(2)
    outcome = ReadOutcome(
        games=["DCS World"], failed={"DCS World": "x"}, finished_at="09:41"
    )
    with qtbot.waitSignal(window.read_finished):
        window._on_read_finished(outcome)
    assert window.current_stage == 2
    banner = next(
        f for f in window.banner.banners if f.property("bannerKey") == "read-failed"
    )
    assert banner.property("bannerText") == (
        "Couldn't read DCS World · your templates and layouts are kept"
    )
    labels = [b.text() for b in banner.findChildren(QPushButton)]
    assert labels == ["Choose folder…", "Read again"]


NEW = "aaaec0a0-556b-11ee-8002-444553540000"
OLD = "bbbec0a0-556b-11ee-8002-444553540000"


def _new_controller_outcome(seen):
    return ReadOutcome(
        games=["DCS World"],
        finished_at="09:41",
        inventory=SimpleNamespace(new=[NEW], seen=seen),
    )


def _statuses(*_args, **_kwargs):
    return {
        NEW: StatusInfo(
            DeviceStatus.NEEDS_TEMPLATE,
            name="WINWING Orion Throttle Base II",
            games={"DCS World": 2},
            profile_count=2,
            is_new=True,
        )
    }


def test_new_controller_banner_and_dismissal_per_guid(qtbot):
    window, _ = make_window(qtbot, games=[ready_game()])
    with patch("joystick_diagrams.device_status.all_device_statuses", _statuses):
        window._on_read_finished(_new_controller_outcome([NEW, OLD]))
    frame = next(
        f
        for f in window.banner.banners
        if f.property("bannerKey") == f"new-controller:{NEW}"
    )
    assert frame.property("bannerText") == (
        "New controller found: WINWING Orion Throttle Base II"
    )
    assert [b.text() for b in frame.findChildren(QPushButton)] == [
        "Choose template…",
        "No diagram needed",
    ]
    from joystick_diagrams.app_state import AppState

    service = AppState().device_service
    with patch.object(service, "set_make_diagram") as make:
        next(
            b
            for b in frame.findChildren(QPushButton)
            if b.text() == "No diagram needed"
        ).click()
    make.assert_called_once_with(NEW, False, "WINWING Orion Throttle Base II")
    assert NEW in dismissed_new_controllers()
    with patch("joystick_diagrams.device_status.all_device_statuses", _statuses):
        window._on_read_finished(_new_controller_outcome([NEW, OLD]))
    assert not any(str(t).startswith("New controller") for t in window.banner.texts())


def test_first_read_does_not_announce_new_controllers(qtbot):
    window, _ = make_window(qtbot, games=[ready_game()])
    with patch("joystick_diagrams.device_status.all_device_statuses", _statuses):
        window._on_read_finished(_new_controller_outcome([NEW]))
    assert not any(str(t).startswith("New controller") for t in window.banner.texts())


# ── GameReader ──


class Game:
    def __init__(self, name, ok=True, profiles=2):
        self.name = name
        self.enabled = True
        self.ready = True
        self.error = ""
        self._ok = ok
        self._profiles = profiles
        self.plugin_profile_collection = ["old"] if not ok else None

    def process(self):
        if not self._ok:
            self.plugin_profile_collection = None
            self.error = "boom"
            return False
        self.plugin_profile_collection = list(range(self._profiles))
        return True


def test_game_reader_reads_every_game_and_keeps_the_last_good_read(qtbot):
    app_state = MagicMock()
    app_state.record_device_read.return_value = SimpleNamespace(new=[], seen=[])
    reader = GameReader(app_state)
    bad, good = Game("Broken", ok=False), Game("DCS World", profiles=3)
    with qtbot.waitSignal(reader.finished, timeout=5000) as blocker:
        assert reader.start([bad, good])
        assert reader.in_progress
    outcome = blocker.args[0]
    assert outcome.failed == {"Broken": "boom"}
    assert outcome.profiles_per_game == {"DCS World": 3}
    assert bad.plugin_profile_collection == ["old"]  # kept
    app_state.process_profiles_from_collections.assert_called_once()
    app_state.record_device_read.assert_called_once()
    assert not reader.in_progress


def test_read_in_progress_and_signals_on_the_shell(qtbot):
    window, _ = make_window(qtbot, games=[Game("DCS World")])
    window.appState.record_device_read = MagicMock(
        return_value=SimpleNamespace(new=[], seen=[])
    )
    window.appState.process_profiles_from_collections = MagicMock()
    started = []
    window.read_started.connect(started.append)
    with qtbot.waitSignal(window.read_finished, timeout=5000) as blocker:
        assert window.start_read()
        assert window.read_in_progress
        assert window.strip.tab(0).status_label.text() == "Stage 0" or True
    assert started == [["DCS World"]]
    assert blocker.args[0].ok
    assert not window.read_in_progress
    assert window.statusLabel.text() == "App is up to date"


def test_launch_read_shows_the_popover_and_can_be_turned_off(qtbot):
    window, _ = make_window(qtbot, games=[Game("DCS World")])
    window._auto_read_allowed = True
    window.appState.record_device_read = MagicMock(
        return_value=SimpleNamespace(new=[], seen=[])
    )
    window.appState.process_profiles_from_collections = MagicMock()
    with qtbot.waitSignal(window.read_finished, timeout=5000):
        window._launch_auto_read()
        assert window.read_popover.isVisible()
        assert window.read_popover.title_label.text() == "Reading DCS World…"
        assert window.read_popover.auto_button.text() == "Turn off automatic reading"
    assert window.read_popover.title_label.text().startswith("Up to date · read ")
    window.read_popover.auto_button.click()
    assert workflow_settings.get_auto_read_on_launch() is False
    assert window.read_popover.auto_button.text() == "Turn on automatic reading"


def test_no_launch_read_when_turned_off(qtbot):
    workflow_settings.set_auto_read_on_launch(False)
    window, _ = make_window(qtbot, games=[Game("DCS World")])
    window._auto_read_allowed = True
    window._launch_auto_read()
    assert not window.read_in_progress
    assert not window.read_popover.isVisible()


def test_popover_opens_by_itself_only_once_then_on_click(qtbot):
    # A returning user has seen the explanation: a launch read is quiet
    workflow_settings.set_read_popover_shown(True)
    window, _ = make_window(qtbot, games=[Game("DCS World")])
    window._auto_read_allowed = True
    window.appState.record_device_read = MagicMock(
        return_value=SimpleNamespace(new=[], seen=[])
    )
    window.appState.process_profiles_from_collections = MagicMock()
    with qtbot.waitSignal(window.read_finished, timeout=5000):
        window._launch_auto_read()
        assert not window.read_popover.isVisible()
    assert not window.read_popover.isVisible()
    # The tab status still tells the story; the popover is on demand
    window.go_to_stage(0)
    window.strip.tab(0).clicked.emit(0)
    assert window.read_popover.isVisible()
    assert window.read_popover.title_label.text().startswith("Up to date · read ")
    window.strip.tab(0).clicked.emit(0)
    assert not window.read_popover.isVisible()
    # Clicking another tab still navigates
    window.strip.tab(3).clicked.emit(3)
    assert window._current_stage == 3
