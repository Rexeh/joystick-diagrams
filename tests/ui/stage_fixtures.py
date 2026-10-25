"""Shared helpers for the four-stage shell tests (1. Setup, 2. Controllers, picker).

Profiles are built with the real ``Profile_``/``Device_`` API and handed to the app
through light wrappers carrying only what ``device_status`` reads, so the status
rules under test are the real ones.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch

from pydantic import Field
from PySide6.QtCore import QCoreApplication, QThreadPool

from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings

STICK = "666ec0a0-556b-11ee-8002-444553540000"
THROTTLE = "777ec0a0-556b-11ee-8002-444553540000"
VJOY = "888ec0a0-556b-11ee-8002-444553540000"
KEYBOARD = "999ec0a0-556b-11ee-8002-444553540000"
TEST_TEMPLATE = Path("tests/data/template_test.svg").resolve()  # BUTTON_1, 2, 10


class Origin:
    def __init__(self, name: str):
        self.name = name
        self.icon = ""


class FakeProfileWrapper:
    def __init__(self, original: Profile_, game: str = "DCS World"):
        self.original_profile = original
        self.profile = deepcopy(original)
        self.profile_origin = Origin(game)
        self.profile_key = f"{game.lower()}_{original.name.lower()}"
        self.profile_name = original.name


def profile_with(name: str = "F-16C") -> Profile_:
    """Stick (button 1), throttle (button 2), a keyboard with one binding (tests
    mark it No diagram by hand) and a vJoy device with nothing bound."""
    profile = Profile_(name)
    profile.add_device(STICK, "Gladiator NXT").create_input(Button(1), "Fire")
    profile.add_device(THROTTLE, "Warthog Throttle").create_input(Button(2), "Gear")
    profile.add_device(KEYBOARD, "Keyboard").create_input(Button(3), "Pause")
    profile.add_device(VJOY, "vJoy Device")
    return profile


def seed_app_state(wrappers=None, profile_wrappers=None):
    """A fresh ``AppState`` with a mocked game list and the given profiles."""
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    manager = MagicMock()
    manager.plugin_wrappers = list(wrappers or [])
    manager.get_enabled_plugin_wrappers.return_value = []
    manager.is_user_plugin.return_value = False
    manager.get_user_plugin_path.return_value = None
    state = AppState(plugin_manager=manager, output_plugin_manager=MagicMock())
    state.profile_wrappers = list(profile_wrappers or [])
    return state


def drain(ms: int = 50) -> None:
    """Let queued signals from the thread pool arrive."""
    pool = QThreadPool.globalInstance()
    pool.waitForDone(5000)
    for _ in range(max(1, ms // 10)):
        QCoreApplication.processEvents()


@contextmanager
def patched_settings():
    """Real-looking settings: the root conftest makes ``get_setting`` always None."""
    store: dict[str, str] = {}

    def put(key: str, value: str) -> None:
        store[key] = value

    with (
        patch("joystick_diagrams.db.db_settings.get_setting", side_effect=store.get),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value", side_effect=put
        ),
    ):
        yield store


# ── A tiny game ──


class FakeGameSettings(PluginSettings):
    game_dir: Path | None = Field(
        default=None,
        title="Game folder",
        json_schema_extra={"is_folder": True},
    )


class FakeGame(PluginInterface):
    plugin_meta = PluginMeta(name="Test Game", version="1.0.0", icon_path="none.ico")
    plugin_settings_model = FakeGameSettings
    candidates: list[Path] = []
    profiles: int = 2
    fail: bool = False

    def process(self) -> ProfileCollection:
        if self.fail:
            raise RuntimeError("boom")
        collection = ProfileCollection()
        for index in range(self.profiles):
            collection.create_profile(f"Profile {index}")
        return collection

    def suggested_paths(self) -> list[Path]:
        return list(self.candidates)


def fake_game_wrapper(candidates=None, enabled=True):
    from joystick_diagrams.plugin_wrapper import PluginWrapper

    plugin = FakeGame()
    plugin.candidates = list(candidates or [])
    wrapper = PluginWrapper(plugin)
    wrapper.enabled = enabled
    return wrapper
