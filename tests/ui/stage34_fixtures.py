"""Seed helpers for the stage 3 (Bindings) and stage 4 (Diagrams) tests.

Not a test module. Builds an ``AppState`` with mocked plugin managers and
``MagicMock`` profile wrappers carrying real ``Profile_``/``Device_`` objects:
a stick (Starter Template, Ready), a throttle (Starter Template, Ready) and a
panel without a template, over two DCS World profiles. ``settings_store``
replaces the settings table with a dict (the root conftest stubs it to None).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_TEMPLATE = REPO_ROOT / "templates" / "Starter Template.svg"
STARTER_KEY = "bundled:Starter Template.svg"
GAME = "DCS World"

STICK = "11111111-0001-11ee-8001-444553540000"
THROTTLE = "22222222-0002-11ee-8002-444553540000"
PANEL = "33333333-0003-11ee-8003-444553540000"
NAMES = {STICK: "Gladiator NXT", THROTTLE: "Warthog Throttle", PANEL: "Button Box"}

# profile → guid → {button: (command, [modifier keys])}
PROFILES: dict[str, dict[str, dict[int, tuple[str, list[str]]]]] = {
    "F-16C": {
        STICK: {1: ("Pickle", ["LShift"]), 2: ("Trigger", []), 99: ("Far away", [])},
        THROTTLE: {1: ("Speed brake", ["LCtrl"])},
        PANEL: {1: ("Lights", [])},
    },
    "A-10C": {
        STICK: {1: ("Fire", [])},
        PANEL: {2: ("Gear", [])},
    },
    "Common": {
        THROTTLE: {3: ("Comms", [])},
    },
}


def make_wrapper(name: str, devices: dict[str, dict[int, tuple[str, list[str]]]]):
    profile = Profile_(name)
    for guid, binds in devices.items():
        device = profile.add_device(guid, NAMES[guid])
        for number, (command, keys) in binds.items():
            device.create_input(Button(number), command)
            for key in keys:
                device.add_modifier_to_input(
                    Button(number), {key}, f"{command} ({key})"
                )
    wrapper = MagicMock()
    wrapper.profile = profile
    wrapper.original_profile = profile
    wrapper.profile_origin.name = GAME
    wrapper.profile_origin.icon = ""
    wrapper.profile_name = name
    wrapper.profile_key = f"{GAME.lower()}_{name.lower()}"
    wrapper.parents = []
    return wrapper


def seed_state(templates: dict[str, Path] | None = None, profiles=None):
    from joystick_diagrams.app_state import AppState

    manager = MagicMock()
    manager.plugin_wrappers = []
    manager.get_enabled_plugin_wrappers.return_value = []
    output = MagicMock()
    output.get_enabled_plugin_wrappers.return_value = []
    state = AppState(plugin_manager=manager, output_plugin_manager=output)
    state.profile_wrappers = [
        make_wrapper(name, devices)
        for name, devices in (PROFILES if profiles is None else profiles).items()
    ]
    templates = (
        {STICK: STARTER_TEMPLATE, THROTTLE: STARTER_TEMPLATE}
        if templates is None
        else templates
    )
    for guid, path in templates.items():
        state.device_service.set_template(guid, str(path))
    return state


@pytest.fixture
def settings_store():
    values: dict[str, str] = {}
    with (
        patch("joystick_diagrams.db.db_settings.get_setting", side_effect=values.get),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value",
            side_effect=values.__setitem__,
        ),
    ):
        yield values


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


class _ShellSignals(QObject):
    read_finished = Signal(object)


class FakeShell(QWidget):
    """Just the shell surface stage pages duck-type (``ui/shell_access``)."""

    def __init__(self):
        super().__init__()
        self._signals = _ShellSignals()
        self.read_finished = self._signals.read_finished
        self.read_in_progress = False
        self.banners: list[tuple[str, list]] = []
        self.status: list[tuple[str, int | None]] = []

    def show_banner(self, text, actions=(), tone="info", **_kwargs):
        self.banners.append((text, list(actions)))

    def clear_banner(self, key=None):
        pass

    def set_status_text(self, text, progress=None):
        self.status.append((text, progress))


if __name__ == "__main__":
    pass
