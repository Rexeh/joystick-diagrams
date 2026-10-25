"""Parent-profile UI round trip (plan 2.4): load -> save -> reload keeps the order.

Pins the pairing between the in-place reverse in
`ProfileWrapper.inherit_parents_into_profile` and the `reversed(...)` display
in `parent_profile_ui.load_profile_parent_maps`. Uses the autouse
`temp_database` from tests/ui/conftest.py so `update_parents_for_profile`
writes to a throwaway sqlite file.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.conflict_strategy import (
    InheritanceConflictStrategy,  # noqa: E402
)
from joystick_diagrams.db import db_profiles  # noqa: E402
from joystick_diagrams.input.button import Button  # noqa: E402
from joystick_diagrams.input.profile import Profile_  # noqa: E402
from joystick_diagrams.profile_wrapper import ProfileWrapper  # noqa: E402

GUID = "aaaa0000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


def _origin(name="TestPlugin"):
    origin = MagicMock()
    origin.name = name
    origin.icon = ""
    return origin


def _wrapper(profile_name: str, *bindings: tuple[int, str]) -> ProfileWrapper:
    profile = Profile_(profile_name)
    device = profile.add_device(GUID, "Stick")
    for button, command in bindings:
        device.create_input(Button(button), command)
    return ProfileWrapper(profile, _origin())


def _list_texts(ui) -> list[str]:
    return [ui.listWidget.item(i).text() for i in range(ui.listWidget.count())]


def _command(wrapper: ProfileWrapper, button: int) -> str | None:
    input_ = wrapper.profile.devices[GUID].get_input("buttons", f"BUTTON_{button}")
    return input_.command if input_ else None


@pytest.mark.uitest
def test_parent_list_round_trip_keeps_order_and_precedence(qapp):
    from joystick_diagrams.app_state import AppState
    from joystick_diagrams.ui.parent_profiles import parent_profile_ui

    manager = MagicMock()
    manager.plugin_wrappers = []
    manager.get_enabled_plugin_wrappers.return_value = []
    state = AppState(plugin_manager=manager, output_plugin_manager=MagicMock())

    child = _wrapper("child", (1, "Child One"))
    p1 = _wrapper("p1", (2, "P1 Two"))
    p2 = _wrapper("p2", (2, "P2 Two"))
    state.profile_wrappers = [child, p1, p2]
    db_profiles.add_profile(child.profile_key)

    with patch(
        "joystick_diagrams.profile_wrapper.get_inheritance_strategy",
        return_value=InheritanceConflictStrategy.KEEP_EXISTING,
    ):
        # User saved [P1, P2] (top to bottom)
        child.update_parents_for_profile([p1, p2])
        precedence_after_save = _command(child, 2)

        ui = parent_profile_ui()
        ui.currentActiveProfile = child
        ui.load_profile_parent_maps(child)
        assert _list_texts(ui) == ["P1", "P2"]

        # Save straight back from the list, then reload from the database
        ui.save_profile_parent_maps()
        child.get_parents_for_profile()
        child.inherit_parents_into_profile()
        ui.load_profile_parent_maps(child)

    assert _list_texts(ui) == ["P1", "P2"]
    assert _command(child, 2) == precedence_after_save == "P2 Two"
