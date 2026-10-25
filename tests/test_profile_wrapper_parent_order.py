"""Characterisation of parent-profile precedence (plan 2.4, no behaviour change).

`ProfileWrapper.inherit_parents_into_profile` reverses `self.parents` **in
place** and `ui/parent_profiles.py:113` displays `reversed(parents)` to undo
it. The two are load-bearing together: changing one without the other flips
parent precedence on every save. These tests pin the current contract so
either side can't drift alone.
"""

from unittest.mock import MagicMock, patch

import pytest

from joystick_diagrams.conflict_strategy import InheritanceConflictStrategy
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.profile_wrapper import ProfileWrapper

GUID = "aaaa0000-0000-0000-0000-000000000001"


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


def _command(wrapper: ProfileWrapper, button: int) -> str | None:
    input_ = wrapper.profile.devices[GUID].get_input("buttons", f"BUTTON_{button}")
    return input_.command if input_ else None


@pytest.fixture()
def child_p1_p2():
    """Child binds BUTTON_1 only; P1 and P2 both bind BUTTON_2 and each one
    extra button, so gap-filling precedence is observable."""
    child = _wrapper("child", (1, "Child One"))
    p1 = _wrapper("p1", (2, "P1 Two"), (3, "P1 Three"))
    p2 = _wrapper("p2", (2, "P2 Two"), (4, "P2 Four"))
    return child, p1, p2


def _inherit(child: ProfileWrapper, parents: list[ProfileWrapper], strategy):
    child.parents = list(parents)
    with patch(
        "joystick_diagrams.profile_wrapper.get_inheritance_strategy",
        return_value=strategy,
    ):
        child.inherit_parents_into_profile()


class TestParentPrecedence:
    def test_parents_list_is_reversed_in_place(self, child_p1_p2):
        child, p1, p2 = child_p1_p2
        _inherit(child, [p1, p2], InheritanceConflictStrategy.KEEP_EXISTING)
        assert child.parents == [p2, p1]

    def test_keep_existing_last_listed_parent_wins_gap_fill(self, child_p1_p2):
        """Current contract for parents [P1, P2]: the child always wins; on a
        gap both parents bind, the *last listed* parent (P2) fills it first."""
        child, p1, p2 = child_p1_p2
        _inherit(child, [p1, p2], InheritanceConflictStrategy.KEEP_EXISTING)
        assert _command(child, 1) == "Child One"
        assert _command(child, 2) == "P2 Two"
        assert _command(child, 3) == "P1 Three"
        assert _command(child, 4) == "P2 Four"

    def test_concatenate_order_follows_the_same_precedence(self, child_p1_p2):
        child, p1, p2 = child_p1_p2
        _inherit(child, [p1, p2], InheritanceConflictStrategy.CONCATENATE)
        assert _command(child, 2) == "P2 Two | [p1] P1 Two"

    def test_modifier_strategy_promotes_lower_precedence_parent(self, child_p1_p2):
        child, p1, p2 = child_p1_p2
        _inherit(child, [p1, p2], InheritanceConflictStrategy.MODIFIER)
        input_ = child.profile.devices[GUID].get_input("buttons", "BUTTON_2")
        assert input_.command == "P2 Two"
        assert [(m.modifiers, m.command) for m in input_.modifiers] == [
            ({"p1"}, "P1 Two")
        ]

    def test_ui_display_order_undoes_the_reverse(self, child_p1_p2):
        """What `ui/parent_profiles.py:113` shows (reversed(parents)) equals the
        order the user saved, so the round trip load -> save -> reload is stable."""
        child, p1, p2 = child_p1_p2
        saved_order = [p1, p2]
        _inherit(child, saved_order, InheritanceConflictStrategy.KEEP_EXISTING)
        displayed = list(reversed(child.parents))
        assert displayed == saved_order

        # Saving the displayed order again reproduces the same merged profile
        before = {n: _command(child, n) for n in (1, 2, 3, 4)}
        _inherit(child, displayed, InheritanceConflictStrategy.KEEP_EXISTING)
        assert {n: _command(child, n) for n in (1, 2, 3, 4)} == before
        assert list(reversed(child.parents)) == saved_order
