"""Every promoted qualifier modifier carries `kind=QUALIFIER` and an explicit
`source` naming the caller (plan 2.2E), and the additive `kind=` plugin API
on `Input_.add_modifier` / `Device_.add_modifier_to_input` works."""

from joystick_diagrams.app_state import _merge_alias_loser_into_winner
from joystick_diagrams.conflict_strategy import (
    QUALIFIER_SOURCE_DEVICE,
    QUALIFIER_SOURCE_PROFILE,
    AliasConflictStrategy,
    InheritanceConflictStrategy,
    apply_input_conflict,
)
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.input import Input_
from joystick_diagrams.input.modifier import Modifier, ModifierKind
from joystick_diagrams.input.profile import Profile_

GUID_A = "aaaa0000-0000-0000-0000-000000000001"
GUID_B = "bbbb0000-0000-0000-0000-000000000002"


def _device(guid: str, name: str, command: str) -> Device_:
    device = Device_(guid, name)
    device.create_input(Button(1), command)
    return device


class TestApplyInputConflictKind:
    def test_promoted_modifier_is_qualifier_with_given_source(self):
        winner = Input_(Button(1), "win")
        loser = Input_(Button(1), "lose")
        apply_input_conflict(
            winner, loser, "Long", AliasConflictStrategy.MODIFIER, "route"
        )
        promoted = winner.modifiers[0]
        assert promoted.modifiers == {"Long"}
        assert promoted.kind is ModifierKind.QUALIFIER
        assert promoted.source == "route"

    def test_source_defaults_to_none_for_legacy_callers(self):
        winner = Input_(Button(1), "win")
        loser = Input_(Button(1), "lose")
        apply_input_conflict(winner, loser, "X", AliasConflictStrategy.MODIFIER)
        assert winner.modifiers[0].kind is ModifierKind.QUALIFIER
        assert winner.modifiers[0].source is None

    def test_loser_real_key_modifiers_keep_their_kind(self):
        winner = Input_(Button(1), "win")
        loser = Input_(Button(1), "lose")
        loser.add_modifier({"LShift"}, "shifted")
        apply_input_conflict(
            winner, loser, "Long", AliasConflictStrategy.MODIFIER, "route"
        )
        carried = winner.modifiers[1]
        assert carried.modifiers == {"LShift"}
        assert carried.kind is ModifierKind.KEY
        assert carried.source is None

    def test_concatenate_creates_no_modifier(self):
        winner = Input_(Button(1), "win")
        loser = Input_(Button(1), "lose")
        apply_input_conflict(
            winner, loser, "Long", AliasConflictStrategy.CONCATENATE, "route"
        )
        assert winner.command == "win | [Long] lose"
        assert winner.modifiers == []


class TestCallerSources:
    def test_profile_merge_marks_qualifier_with_profile_source(self):
        child = Profile_("child")
        child.devices[GUID_A] = _device(GUID_A, "Stick", "Child Cmd")
        parent = Profile_("Parent Profile")
        parent.devices[GUID_A] = _device(GUID_A, "Stick", "Parent Cmd")

        merged = child.merge_profiles(parent, InheritanceConflictStrategy.MODIFIER)

        promoted = merged.devices[GUID_A].get_input("buttons", "BUTTON_1").modifiers[0]
        assert promoted.modifiers == {"Parent Profile"}
        assert promoted.command == "Parent Cmd"
        assert promoted.kind is ModifierKind.QUALIFIER
        assert promoted.source == QUALIFIER_SOURCE_PROFILE == "profile"

    def test_device_alias_merge_marks_qualifier_with_device_source(self):
        winner = _device(GUID_A, "Winner Stick", "Winner Cmd")
        loser = _device(GUID_B, "Loser Stick", "Loser Cmd")

        _merge_alias_loser_into_winner(winner, loser, AliasConflictStrategy.MODIFIER)

        promoted = winner.get_input("buttons", "BUTTON_1").modifiers[0]
        assert promoted.modifiers == {"Loser Stick"}
        assert promoted.kind is ModifierKind.QUALIFIER
        assert promoted.source == QUALIFIER_SOURCE_DEVICE == "device"


class TestAdditivePluginApi:
    def test_add_modifier_defaults_to_key_kind(self):
        input_ = Input_(Button(1), "cmd")
        input_.add_modifier({"LShift"}, "shifted")
        assert input_.modifiers[0].kind is ModifierKind.KEY

    def test_add_modifier_accepts_kind_keyword(self):
        input_ = Input_(Button(1), "cmd")
        input_.add_modifier({"Mode 2"}, "alt", kind=ModifierKind.QUALIFIER)
        assert input_.modifiers[0].kind is ModifierKind.QUALIFIER
        assert input_.modifiers[0].source is None

    def test_add_modifier_last_write_wins_for_kind_too(self):
        input_ = Input_(Button(1), "cmd")
        input_.add_modifier({"X"}, "first")
        input_.add_modifier({"X"}, "second", kind=ModifierKind.QUALIFIER)
        assert len(input_.modifiers) == 1
        assert input_.modifiers[0].command == "second"
        assert input_.modifiers[0].kind is ModifierKind.QUALIFIER

    def test_device_add_modifier_to_input_passes_kind_for_shell_and_existing(self):
        device = Device_(GUID_A, "Stick")
        # Shell input path
        device.add_modifier_to_input(
            Button(1), {"Mode"}, "shell", kind=ModifierKind.QUALIFIER
        )
        shell = device.get_input("buttons", "BUTTON_1")
        assert shell.command == ""
        assert shell.modifiers[0].kind is ModifierKind.QUALIFIER
        # Existing input path
        device.create_input(Button(2), "Fire")
        device.add_modifier_to_input(Button(2), {"LShift"}, "Alt Fire")
        assert device.get_input("buttons", "BUTTON_2").modifiers[0].kind is (
            ModifierKind.KEY
        )

    def test_dedup_ignores_kind(self):
        """Set-only dedup is unchanged: a KEY {Shift} and a QUALIFIER {Shift}
        collide, and the winner keeps its slot (documented limitation)."""
        winner = Input_(Button(1), "win")
        winner.add_modifier({"Shift"}, "real shift")
        loser = Input_(Button(1), "lose")
        loser.modifiers.append(
            Modifier({"Shift"}, "profile shift", kind=ModifierKind.QUALIFIER)
        )
        apply_input_conflict(
            winner, loser, "P", InheritanceConflictStrategy.KEEP_EXISTING, "profile"
        )
        assert len(winner.modifiers) == 1
        assert winner.modifiers[0].command == "real shift"
        assert winner.modifiers[0].kind is ModifierKind.KEY
