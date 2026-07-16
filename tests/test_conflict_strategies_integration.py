"""Scenario-matrix tests for configurable conflict-resolution strategies.

Covers Groups B (inheritance only), C (alias only), D (inheritance + alias
composed), and E (variants) from the plan. Strategies are passed explicitly
to the merge helpers so no settings fixture is required.
"""

from unittest.mock import patch

import pytest

from joystick_diagrams.app_state import AppState
from joystick_diagrams.conflict_strategy import (
    AliasConflictStrategy,
    InheritanceConflictStrategy,
)
from joystick_diagrams.db.device_alias_service import DeviceAliasService
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.profile import Profile_

GUID_D1 = "11110000-0000-0000-0000-000000000001"
GUID_D2 = "22220000-0000-0000-0000-000000000002"
GUID_D3 = "33330000-0000-0000-0000-000000000003"


# --- Helpers ----------------------------------------------------------------


def _alias_service(aliases):
    """Build a DeviceAliasService backed by the supplied (source, target) pairs."""
    with patch(
        "joystick_diagrams.db.device_alias_service.db_device_aliases"
    ) as mock_db:
        mock_db.get_all_aliases.return_value = aliases
        return DeviceAliasService()


def _profile(name, *devices):
    """Build a Profile_ from (guid, device_name, [(btn_id, command), ...]) tuples."""
    profile = Profile_(name)
    for guid, dev_name, buttons in devices:
        dev = profile.add_device(guid, dev_name)
        for btn_id, command in buttons:
            dev.create_input(Button(btn_id), command)
    return profile


def _btn_input(profile, guid, btn_key):
    return profile.devices[guid].inputs["buttons"][btn_key]


def _modifier_commands(input_):
    """Return {frozenset(keys): command} for convenient assertion."""
    return {frozenset(m.modifiers): m.command for m in input_.modifiers}


# ============================================================================
# Group B — inheritance only (P1 child inherits from P2 parent)
# ============================================================================


class TestGroupBInheritanceOnly:
    """Child wins primary; parent contributes per strategy."""

    def test_b1_parent_has_no_binding_child_wins(self):
        child = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))
        parent = _profile("P2", (GUID_D1, "D1", []))

        merged = child.merge_profiles(
            parent, strategy=InheritanceConflictStrategy.KEEP_EXISTING
        )

        assert _btn_input(merged, GUID_D1, "BUTTON_1").command == "Shoot"
        assert _btn_input(merged, GUID_D1, "BUTTON_1").modifiers == []

    def test_b2_child_has_no_binding_parent_gap_fills(self):
        child = _profile("P1", (GUID_D1, "D1", []))
        parent = _profile("P2", (GUID_D1, "D1", [(1, "Aim")]))

        for strategy in InheritanceConflictStrategy:
            merged = child.merge_profiles(parent, strategy=strategy)
            assert (
                _btn_input(merged, GUID_D1, "BUTTON_1").command == "Aim"
            ), f"gap-fill broke under {strategy}"

    def test_b3a_conflict_keep_existing_drops_parent(self):
        child = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))
        parent = _profile("P2", (GUID_D1, "D1", [(1, "Aim")]))

        merged = child.merge_profiles(
            parent, strategy=InheritanceConflictStrategy.KEEP_EXISTING
        )

        result = _btn_input(merged, GUID_D1, "BUTTON_1")
        assert result.command == "Shoot"
        assert result.modifiers == []

    def test_b3b_conflict_concatenate_joins_child_then_parent(self):
        child = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))
        parent = _profile("P2", (GUID_D1, "D1", [(1, "Aim")]))

        merged = child.merge_profiles(
            parent, strategy=InheritanceConflictStrategy.CONCATENATE
        )

        result = _btn_input(merged, GUID_D1, "BUTTON_1")
        assert result.command == "Shoot | [P2] Aim"
        assert result.modifiers == []

    def test_b3c_conflict_modifier_promotes_parent_under_parent_name(self):
        child = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))
        parent = _profile("P2", (GUID_D1, "D1", [(1, "Aim")]))

        merged = child.merge_profiles(
            parent, strategy=InheritanceConflictStrategy.MODIFIER
        )

        result = _btn_input(merged, GUID_D1, "BUTTON_1")
        assert result.command == "Shoot"
        assert _modifier_commands(result) == {frozenset({"P2"}): "Aim"}

    def test_b4_parent_modifiers_merge_into_child_with_keep_existing(self):
        child = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))
        parent = Profile_("P2")
        parent_dev = parent.add_device(GUID_D1, "D1")
        parent_dev.create_input(Button(1), "Aim")
        parent_dev.add_modifier_to_input(Button(1), {"ctrl"}, "AltFire")

        merged = child.merge_profiles(
            parent, strategy=InheritanceConflictStrategy.KEEP_EXISTING
        )

        result = _btn_input(merged, GUID_D1, "BUTTON_1")
        assert result.command == "Shoot"
        assert _modifier_commands(result) == {frozenset({"ctrl"}): "AltFire"}

    def test_b5_modifier_keyset_collision_child_wins(self):
        child = Profile_("P1")
        child_dev = child.add_device(GUID_D1, "D1")
        child_dev.create_input(Button(1), "Shoot")
        child_dev.add_modifier_to_input(Button(1), {"ctrl"}, "ChildAlt")

        parent = Profile_("P2")
        parent_dev = parent.add_device(GUID_D1, "D1")
        parent_dev.create_input(Button(1), "Aim")
        parent_dev.add_modifier_to_input(Button(1), {"ctrl"}, "ParentAlt")
        parent_dev.add_modifier_to_input(Button(1), {"shift"}, "ParentShift")

        merged = child.merge_profiles(
            parent, strategy=InheritanceConflictStrategy.MODIFIER
        )

        result = _btn_input(merged, GUID_D1, "BUTTON_1")
        mods = _modifier_commands(result)
        # ctrl-key collision → child's ChildAlt wins, parent's ParentAlt skipped
        assert mods[frozenset({"ctrl"})] == "ChildAlt"
        # shift key is new → parent's modifier carried over
        assert mods[frozenset({"shift"})] == "ParentShift"
        # Parent's primary "Aim" promoted under {"P2"}
        assert mods[frozenset({"P2"})] == "Aim"

    def test_b6_modifier_qualifier_collision_first_promoted_wins(self):
        """If parent already has a modifier keyed by the parent-name qualifier,
        the auto-promoted modifier (added first) wins; parent's original
        same-keyed modifier is skipped."""
        child = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))
        parent = Profile_("P2")
        parent_dev = parent.add_device(GUID_D1, "D1")
        parent_dev.create_input(Button(1), "Aim")
        parent_dev.add_modifier_to_input(Button(1), {"P2"}, "ParentPreExisting")

        merged = child.merge_profiles(
            parent, strategy=InheritanceConflictStrategy.MODIFIER
        )

        result = _btn_input(merged, GUID_D1, "BUTTON_1")
        assert result.command == "Shoot"
        # Promotion wins; loser's {"P2"}-keyed modifier skipped on collision.
        assert _modifier_commands(result) == {frozenset({"P2"}): "Aim"}


# ============================================================================
# Group C — alias only (D2 -> D1, no inheritance)
# ============================================================================


class TestGroupCAliasOnly:
    """Source wins primary; target contributes per strategy."""

    def test_c1_target_binding_only_source_absent_target_preserved(self):
        """Target has binding, source device not present → canonical keeps target."""
        alias_service = _alias_service([(GUID_D2, GUID_D1)])
        profile = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))

        result = AppState._apply_aliases_to_profile(
            profile, alias_service, strategy=AliasConflictStrategy.MODIFIER
        )

        assert _btn_input(result, GUID_D1, "BUTTON_1").command == "Shoot"

    def test_c2_source_binding_only_gap_fills_under_canonical(self):
        alias_service = _alias_service([(GUID_D2, GUID_D1)])

        for strategy in AliasConflictStrategy:
            result = AppState._apply_aliases_to_profile(
                _profile("P1", (GUID_D2, "D2", [(1, "Dodge")])),
                alias_service,
                strategy=strategy,
            )
            assert (
                _btn_input(result, GUID_D1, "BUTTON_1").command == "Dodge"
            ), f"alias gap-fill broke under {strategy}"
            # original GUID should no longer be present
            assert GUID_D2 not in result.devices

    def test_c3a_conflict_modifier_source_wins_primary(self):
        alias_service = _alias_service([(GUID_D2, GUID_D1)])
        profile = _profile(
            "P1",
            (GUID_D1, "D1-Name", [(1, "Shoot")]),
            (GUID_D2, "D2-Name", [(1, "Dodge")]),
        )

        result = AppState._apply_aliases_to_profile(
            profile, alias_service, strategy=AliasConflictStrategy.MODIFIER
        )

        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        assert input_.command == "Dodge"  # source wins primary
        assert _modifier_commands(input_) == {frozenset({"D1-Name"}): "Shoot"}
        assert GUID_D2 not in result.devices

    def test_c3b_conflict_concatenate_source_first_target_second(self):
        alias_service = _alias_service([(GUID_D2, GUID_D1)])
        profile = _profile(
            "P1",
            (GUID_D1, "D1-Name", [(1, "Shoot")]),
            (GUID_D2, "D2-Name", [(1, "Dodge")]),
        )

        result = AppState._apply_aliases_to_profile(
            profile, alias_service, strategy=AliasConflictStrategy.CONCATENATE
        )

        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        assert input_.command == "Dodge | [D1-Name] Shoot"
        assert input_.modifiers == []

    def test_c4_three_way_alias_modifier_first_source_wins_primary(self):
        """D2→D1 and D3→D1. First-iterated source wins primary; subsequent
        sources and the target become modifiers."""
        alias_service = _alias_service([(GUID_D2, GUID_D1), (GUID_D3, GUID_D1)])
        profile = _profile(
            "P1",
            (GUID_D1, "D1-Name", [(1, "C")]),
            (GUID_D2, "D2-Name", [(1, "A")]),
            (GUID_D3, "D3-Name", [(1, "B")]),
        )

        result = AppState._apply_aliases_to_profile(
            profile, alias_service, strategy=AliasConflictStrategy.MODIFIER
        )

        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        assert input_.command == "A"  # D2 first-iterated source wins
        mods = _modifier_commands(input_)
        assert mods[frozenset({"D3-Name"})] == "B"
        assert mods[frozenset({"D1-Name"})] == "C"

    def test_c4_three_way_alias_concatenate_source_iteration_then_target(self):
        alias_service = _alias_service([(GUID_D2, GUID_D1), (GUID_D3, GUID_D1)])
        profile = _profile(
            "P1",
            (GUID_D1, "D1-Name", [(1, "C")]),
            (GUID_D2, "D2-Name", [(1, "A")]),
            (GUID_D3, "D3-Name", [(1, "B")]),
        )

        result = AppState._apply_aliases_to_profile(
            profile, alias_service, strategy=AliasConflictStrategy.CONCATENATE
        )

        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        # First source wins primary, subsequent sources and target appended in
        # order — each loser segment prefixed with its device name.
        assert input_.command == "A | [D3-Name] B | [D1-Name] C"

    def test_c5_source_with_modifiers_no_primary_conflict_gap_fill(self):
        """Source has input (with modifiers) on a key the target lacks → copy whole."""
        alias_service = _alias_service([(GUID_D2, GUID_D1)])
        profile = Profile_("P1")
        profile.add_device(GUID_D1, "D1-Name").create_input(Button(2), "TargetOnly")
        src = profile.add_device(GUID_D2, "D2-Name")
        src.create_input(Button(1), "SourceOnly")
        src.add_modifier_to_input(Button(1), {"ctrl"}, "SourceAlt")

        result = AppState._apply_aliases_to_profile(
            profile, alias_service, strategy=AliasConflictStrategy.MODIFIER
        )

        btn1 = _btn_input(result, GUID_D1, "BUTTON_1")
        assert btn1.command == "SourceOnly"
        assert _modifier_commands(btn1) == {frozenset({"ctrl"}): "SourceAlt"}
        assert _btn_input(result, GUID_D1, "BUTTON_2").command == "TargetOnly"

    def test_c6_both_sides_have_modifiers_on_conflict_dedup(self):
        """Both sides have primary AND modifiers on same input → strategy applies
        to primary; modifiers merge via key-set dedup (winner=source wins)."""
        alias_service = _alias_service([(GUID_D2, GUID_D1)])

        profile = Profile_("P1")
        tgt = profile.add_device(GUID_D1, "D1-Name")
        tgt.create_input(Button(1), "Shoot")
        tgt.add_modifier_to_input(Button(1), {"ctrl"}, "TargetCtrl")

        src = profile.add_device(GUID_D2, "D2-Name")
        src.create_input(Button(1), "Dodge")
        src.add_modifier_to_input(Button(1), {"ctrl"}, "SourceCtrl")
        src.add_modifier_to_input(Button(1), {"alt"}, "SourceAlt")

        result = AppState._apply_aliases_to_profile(
            profile, alias_service, strategy=AliasConflictStrategy.MODIFIER
        )

        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        # Source wins primary.
        assert input_.command == "Dodge"
        mods = _modifier_commands(input_)
        # Source is winner → its {"ctrl"} modifier stays; target's {"ctrl"} dropped on collision.
        assert mods[frozenset({"ctrl"})] == "SourceCtrl"
        # Source's {"alt"} carried through.
        assert mods[frozenset({"alt"})] == "SourceAlt"
        # Target's primary "Shoot" promoted under target's device name.
        assert mods[frozenset({"D1-Name"})] == "Shoot"


# ============================================================================
# Group D — inheritance AND alias composed
# ============================================================================


def _run_inheritance_then_alias(
    child_profile: Profile_,
    parent_profile: Profile_,
    inheritance_strategy: InheritanceConflictStrategy,
    alias_strategy: AliasConflictStrategy,
    aliases,
):
    """Mirror the app pipeline: inheritance first, then alias."""
    merged = child_profile.merge_profiles(parent_profile, strategy=inheritance_strategy)
    alias_service = _alias_service(aliases)
    return AppState._apply_aliases_to_profile(
        merged, alias_service, strategy=alias_strategy
    )


def _group_d_profiles():
    """Standard Group D setup:
    P1/D1.B1 = "Shoot"
    P2/D1.B1 = "Aim", P2/D2.B1 = "Dodge"
    alias D2 -> D1, P1 child of P2
    """
    child = _profile("P1", (GUID_D1, "D1-Name", [(1, "Shoot")]))
    parent = _profile(
        "P2",
        (GUID_D1, "D1-Name", [(1, "Aim")]),
        (GUID_D2, "D2-Name", [(1, "Dodge")]),
    )
    return child, parent


class TestGroupDInheritanceAndAlias:
    def test_d1_keep_existing_plus_modifier(self):
        child, parent = _group_d_profiles()
        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.KEEP_EXISTING,
            AliasConflictStrategy.MODIFIER,
            [(GUID_D2, GUID_D1)],
        )
        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        assert input_.command == "Dodge"  # source wins alias step
        # Parent's "Aim" was dropped by KEEP_EXISTING; post-inheritance D1 held "Shoot".
        # Alias step promotes that "Shoot" as a modifier keyed by target device name.
        assert _modifier_commands(input_) == {frozenset({"D1-Name"}): "Shoot"}

    def test_d2_keep_existing_plus_concatenate(self):
        child, parent = _group_d_profiles()
        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.KEEP_EXISTING,
            AliasConflictStrategy.CONCATENATE,
            [(GUID_D2, GUID_D1)],
        )
        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        # "Aim" dropped by inheritance; source "Dodge" + target "Shoot".
        assert input_.command == "Dodge | [D1-Name] Shoot"
        assert input_.modifiers == []

    def test_d3_concatenate_plus_modifier(self):
        child, parent = _group_d_profiles()
        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.CONCATENATE,
            AliasConflictStrategy.MODIFIER,
            [(GUID_D2, GUID_D1)],
        )
        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        # Post-inheritance D1 holds "Shoot | [P2] Aim"; alias step promotes it as modifier.
        assert input_.command == "Dodge"
        assert _modifier_commands(input_) == {
            frozenset({"D1-Name"}): "Shoot | [P2] Aim"
        }

    def test_d4_concatenate_plus_concatenate(self):
        child, parent = _group_d_profiles()
        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.CONCATENATE,
            AliasConflictStrategy.CONCATENATE,
            [(GUID_D2, GUID_D1)],
        )
        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        # Full history preserved in primary; each loser carries its qualifier.
        # Inheritance merged D1 to "Shoot | [P2] Aim"; alias then folds source
        # "Dodge" (winner) with target D1-Name as the loser segment.
        assert input_.command == "Dodge | [D1-Name] Shoot | [P2] Aim"
        assert input_.modifiers == []

    def test_d5_modifier_plus_modifier(self):
        child, parent = _group_d_profiles()
        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.MODIFIER,
            AliasConflictStrategy.MODIFIER,
            [(GUID_D2, GUID_D1)],
        )
        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        # Post-inheritance D1: primary="Shoot", modifier {"P2"}: "Aim".
        # Alias step: source "Dodge" wins primary; target's "Shoot" promoted under
        # D1-Name. Target's existing {"P2"}: "Aim" modifier carried through.
        assert input_.command == "Dodge"
        mods = _modifier_commands(input_)
        assert mods[frozenset({"D1-Name"})] == "Shoot"
        assert mods[frozenset({"P2"})] == "Aim"

    def test_d6_modifier_plus_concatenate(self):
        child, parent = _group_d_profiles()
        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.MODIFIER,
            AliasConflictStrategy.CONCATENATE,
            [(GUID_D2, GUID_D1)],
        )
        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        # Post-inheritance D1: primary="Shoot", mod {"P2"}: "Aim".
        # Alias CONCATENATE: "Dodge | [D1-Name] Shoot"; target's {"P2"}: "Aim"
        # modifier carried through.
        assert input_.command == "Dodge | [D1-Name] Shoot"
        assert _modifier_commands(input_) == {frozenset({"P2"}): "Aim"}


# ============================================================================
# Group E — variants
# ============================================================================


class TestGroupEVariants:
    def test_e1_child_holds_source_device(self):
        """Child has D2 (source), parent has D1 (target). After inheritance,
        both devices exist on the child; alias step merges D2 into D1."""
        child = _profile("P1", (GUID_D2, "D2-Name", [(1, "Dodge")]))
        parent = _profile("P2", (GUID_D1, "D1-Name", [(1, "Shoot")]))

        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.KEEP_EXISTING,
            AliasConflictStrategy.MODIFIER,
            [(GUID_D2, GUID_D1)],
        )

        input_ = _btn_input(result, GUID_D1, "BUTTON_1")
        assert input_.command == "Dodge"  # source wins
        assert _modifier_commands(input_) == {frozenset({"D1-Name"}): "Shoot"}
        assert GUID_D2 not in result.devices

    def test_e2_alias_target_only_present_via_inheritance(self):
        """Child has no D1 at all; parent has D1. After inheritance, D1
        appears on child via gap-fill, and the alias step still works."""
        child = _profile("P1", (GUID_D2, "D2-Name", [(1, "Dodge")]))
        parent = _profile("P2", (GUID_D1, "D1-Name", [(1, "Shoot")]))

        result = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.KEEP_EXISTING,
            AliasConflictStrategy.CONCATENATE,
            [(GUID_D2, GUID_D1)],
        )

        assert (
            _btn_input(result, GUID_D1, "BUTTON_1").command == "Dodge | [D1-Name] Shoot"
        )
        assert GUID_D2 not in result.devices

    def test_e4_strategy_switch_changes_output(self):
        """Same inputs under two different strategy pairs produce different output."""
        child, parent = _group_d_profiles()
        out_keep_concat = _run_inheritance_then_alias(
            child,
            parent,
            InheritanceConflictStrategy.KEEP_EXISTING,
            AliasConflictStrategy.CONCATENATE,
            [(GUID_D2, GUID_D1)],
        )
        # Need fresh profiles because merge_profiles/_apply_aliases may mutate.
        child2, parent2 = _group_d_profiles()
        out_mod_mod = _run_inheritance_then_alias(
            child2,
            parent2,
            InheritanceConflictStrategy.MODIFIER,
            AliasConflictStrategy.MODIFIER,
            [(GUID_D2, GUID_D1)],
        )

        a = _btn_input(out_keep_concat, GUID_D1, "BUTTON_1")
        b = _btn_input(out_mod_mod, GUID_D1, "BUTTON_1")
        assert a.command != b.command or a.modifiers != b.modifiers

    def test_e5_no_conflicts_strategies_have_no_effect(self):
        """All bindings unique → output identical regardless of strategy."""
        outputs = []
        for inh in InheritanceConflictStrategy:
            for alias in AliasConflictStrategy:
                c = _profile("P1", (GUID_D1, "D1-Name", [(1, "Shoot")]))
                p = _profile(
                    "P2",
                    (GUID_D1, "D1-Name", [(2, "Aim")]),
                    (GUID_D2, "D2-Name", [(3, "Dodge")]),
                )
                result = _run_inheritance_then_alias(
                    c, p, inh, alias, [(GUID_D2, GUID_D1)]
                )
                d1 = result.devices[GUID_D1]
                outputs.append(
                    {
                        k: (v.command, _modifier_commands(v))
                        for k, v in d1.inputs["buttons"].items()
                    }
                )

        # Every combination should produce the same per-button state.
        first = outputs[0]
        for snapshot in outputs[1:]:
            assert snapshot == first


# ============================================================================
# Group F — strategy parameter defaults
# ============================================================================


class TestStrategyDefaults:
    def test_merge_profiles_default_is_keep_existing(self):
        """Calling merge_profiles without a strategy preserves current behaviour."""
        child = _profile("P1", (GUID_D1, "D1", [(1, "Shoot")]))
        parent = _profile("P2", (GUID_D1, "D1", [(1, "Aim")]))

        merged = child.merge_profiles(parent)

        result = _btn_input(merged, GUID_D1, "BUTTON_1")
        assert result.command == "Shoot"
        assert result.modifiers == []


# ============================================================================
# Parametrized D1-D6 — the full 3-way compose matrix
# ============================================================================


@pytest.mark.parametrize(
    "inh_strategy,alias_strategy,expected_primary,expected_mods",
    [
        (
            InheritanceConflictStrategy.KEEP_EXISTING,
            AliasConflictStrategy.MODIFIER,
            "Dodge",
            {frozenset({"D1-Name"}): "Shoot"},
        ),
        (
            InheritanceConflictStrategy.KEEP_EXISTING,
            AliasConflictStrategy.CONCATENATE,
            "Dodge | [D1-Name] Shoot",
            {},
        ),
        (
            InheritanceConflictStrategy.CONCATENATE,
            AliasConflictStrategy.MODIFIER,
            "Dodge",
            {frozenset({"D1-Name"}): "Shoot | [P2] Aim"},
        ),
        (
            InheritanceConflictStrategy.CONCATENATE,
            AliasConflictStrategy.CONCATENATE,
            "Dodge | [D1-Name] Shoot | [P2] Aim",
            {},
        ),
        (
            InheritanceConflictStrategy.MODIFIER,
            AliasConflictStrategy.MODIFIER,
            "Dodge",
            {
                frozenset({"D1-Name"}): "Shoot",
                frozenset({"P2"}): "Aim",
            },
        ),
        (
            InheritanceConflictStrategy.MODIFIER,
            AliasConflictStrategy.CONCATENATE,
            "Dodge | [D1-Name] Shoot",
            {frozenset({"P2"}): "Aim"},
        ),
    ],
    ids=["D1", "D2", "D3", "D4", "D5", "D6"],
)
def test_group_d_matrix(inh_strategy, alias_strategy, expected_primary, expected_mods):
    child, parent = _group_d_profiles()
    result = _run_inheritance_then_alias(
        child, parent, inh_strategy, alias_strategy, [(GUID_D2, GUID_D1)]
    )
    input_ = _btn_input(result, GUID_D1, "BUTTON_1")
    assert input_.command == expected_primary
    assert _modifier_commands(input_) == expected_mods
