"""Seed helpers for the Layout screen tests and the screenshot driver.

Not a test module (no ``test_`` prefix). Builds an ``AppState`` with mocked
plugin managers, real ``Profile_``/``Device_`` objects carrying modifier
bindings, ``MagicMock`` profile wrappers (as ``tests/ui/test_appearance_page.py``
does) and a template assigned to the device in the (temporary) database.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from joystick_diagrams.db.db_device_management import add_update_device_template_path
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_TEMPLATE = REPO_ROOT / "templates" / "Starter Template.svg"
DEVICE_GUID = "666ec0a0-556b-11ee-8002-444553540000"
DEVICE_NAME = "Gladiator NXT"
PLUGIN_NAME = "DCS World"

# profile name → {button number: (command, [modifier keys])}
DEFAULT_PROFILES: dict[str, dict[int, tuple[str, list[str]]]] = {
    "F-16C": {
        1: ("Pickle", ["LShift", "LCtrl", "LAlt"]),
        2: ("Trigger", ["LShift", "LCtrl"]),
        3: ("Gear", ["LShift"]),
        4: ("Flaps", []),
    },
    "Mirage": {
        1: ("Fire", ["LShift"]),
        2: ("Radar", ["LCtrl", "LAlt", "LWin", "RShift"]),
    },
}


def make_wrapper(name: str, binds: dict[int, tuple[str, list[str]]]):
    profile = Profile_(name)
    device = profile.add_device(DEVICE_GUID, DEVICE_NAME)
    for number, (command, keys) in binds.items():
        device.create_input(Button(number), command)
        for key in keys:
            device.add_modifier_to_input(Button(number), {key}, f"{command} ({key})")
    wrapper = MagicMock()
    wrapper.profile = profile
    wrapper.original_profile = profile
    wrapper.profile_origin.name = PLUGIN_NAME
    wrapper.profile_origin.icon = ""
    wrapper.profile_name = name
    wrapper.profile_key = f"{PLUGIN_NAME.lower()}_{name.lower()}"
    wrapper.parents = []
    return wrapper


def seed_layout_state(
    template_path: Path = STARTER_TEMPLATE,
    profiles: dict[str, dict[int, tuple[str, list[str]]]] | None = None,
    assign_template: bool = True,
):
    """``AppState`` with profiles for one device that uses ``template_path``."""
    from joystick_diagrams.app_state import AppState

    manager = MagicMock()
    manager.plugin_wrappers = []
    manager.get_enabled_plugin_wrappers.return_value = []
    output = MagicMock()
    output.get_enabled_plugin_wrappers.return_value = []
    state = AppState(plugin_manager=manager, output_plugin_manager=output)
    state.profile_wrappers = [
        make_wrapper(name, binds)
        for name, binds in (profiles or DEFAULT_PROFILES).items()
    ]
    if assign_template:
        add_update_device_template_path(DEVICE_GUID, str(template_path))
    return state


if __name__ == "__main__":
    pass
