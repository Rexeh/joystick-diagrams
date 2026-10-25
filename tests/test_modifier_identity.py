"""Unit tests for the pure modifier identity layer (plan 2.2B/C, 8.5)."""

from unittest.mock import MagicMock, patch

import pytest

from joystick_diagrams import modifier_identity as mi
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.modifier import Modifier, ModifierKind
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.modifier_identity import (
    DEVICE_INPUT_CANONICAL,
    SEED_ALIASES,
    SEED_MODIFIER_KEYS,
    ModifierKeyAlias,
    ModifierKeyDisplay,
    ModifierKeyGroup,
    ModifierKeyInfo,
    ModifierKeyStyle,
    ModifierRegistrySnapshot,
    canonical_keys,
    canonical_of,
    combo_style,
    contrast_ratio,
    discover_modifier_keys,
    group_of,
    is_device_input_key,
    resolve_key,
    resolve_keys,
    resolve_modifier,
    text_safe_colour,
)

GUID = "aaaa0000-0000-0000-0000-000000000001"


def snap(**flags) -> ModifierRegistrySnapshot:
    return ModifierRegistrySnapshot.default(**flags)


# ── Settings accessors ────────────────────────────────────────────────


class TestSettings:
    def test_defaults_when_unset(self):
        # autouse conftest patch returns None for every setting
        assert mi.modifier_colouring_enabled() is False
        assert mi.modifier_sides_merged() is True
        assert mi.get_modifier_key_display() is ModifierKeyDisplay.ORIGINAL

    def test_values_are_read_at_call_time(self):
        with patch(
            "joystick_diagrams.db.db_settings.get_setting", return_value="true"
        ) as get:
            assert mi.modifier_colouring_enabled() is True
            get.assert_called_with(mi.MODIFIER_COLOURING_SETTING_KEY)
        with patch(
            "joystick_diagrams.db.db_settings.get_setting", return_value="false"
        ):
            assert mi.modifier_sides_merged() is False
        with patch(
            "joystick_diagrams.db.db_settings.get_setting", return_value="SIMPLIFIED"
        ):
            assert mi.get_modifier_key_display() is ModifierKeyDisplay.SIMPLIFIED

    def test_invalid_display_falls_back_to_default(self):
        with patch(
            "joystick_diagrams.db.db_settings.get_setting", return_value="WEIRD"
        ):
            assert mi.get_modifier_key_display() is ModifierKeyDisplay.ORIGINAL

    def test_setters_write_string_values(self):
        with patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value"
        ) as write:
            mi.set_modifier_colouring_enabled(True)
            mi.set_modifier_sides_merged(False)
            mi.set_modifier_key_display(ModifierKeyDisplay.SIMPLIFIED)
        assert write.call_args_list[0].args == (
            mi.MODIFIER_COLOURING_SETTING_KEY,
            "true",
        )
        assert write.call_args_list[1].args == (
            mi.MODIFIER_SIDES_MERGED_SETTING_KEY,
            "false",
        )
        assert write.call_args_list[2].args == (
            mi.MODIFIER_KEY_DISPLAY_SETTING_KEY,
            "SIMPLIFIED",
        )

    def test_snapshot_build_reads_flags_from_settings(self):
        with patch("joystick_diagrams.db.db_settings.get_setting", return_value="true"):
            built = ModifierRegistrySnapshot.build([], [])
        assert built.colouring_enabled is True
        assert built.sides_merged is True


# ── Classification ────────────────────────────────────────────────────


class TestGrouping:
    @pytest.mark.parametrize(
        "raw",
        [
            "JOY_BTN3",
            "joy_btn12",
            "JOY_BTN_POV1_U",
            "BUTTON_108",
            "POV_1_UL",
            "AXIS_X",
            "AXIS_SLIDER_1",
        ],
    )
    def test_device_input_keys(self, raw):
        assert is_device_input_key(raw)
        assert group_of(raw) is ModifierKeyGroup.DEVICE_INPUT

    @pytest.mark.parametrize("raw", ["LShift", "lalt", "BMS DX Shift", "Shift", "Apps"])
    def test_keyboard_keys(self, raw):
        assert group_of(raw) is ModifierKeyGroup.KEYBOARD

    def test_qualifier_kind_wins_over_pattern(self):
        assert (
            group_of("BUTTON_108", ModifierKind.QUALIFIER) is ModifierKeyGroup.QUALIFIER
        )
        assert group_of("Shift", ModifierKind.QUALIFIER) is ModifierKeyGroup.QUALIFIER


# ── Seeds ─────────────────────────────────────────────────────────────


class TestSeeds:
    def test_seed_groups_have_okabe_ito_colours_and_rank_order(self):
        groups = {info.canonical: info for _, info in SEED_MODIFIER_KEYS}
        assert groups["Shift"].style.colour == "#0072B2"
        assert groups["Ctrl"].style.colour == "#D55E00"
        assert groups["Alt"].style.colour == "#009E73"
        assert groups["Win"].style.colour == "#CC79A7"
        assert groups[DEVICE_INPUT_CANONICAL].style.colour == "#56B4E9"
        ordered = [
            info.canonical
            for _, info in sorted(SEED_MODIFIER_KEYS, key=lambda s: s[1].priority)
        ]
        assert ordered == ["Ctrl", "Alt", "Shift", "Win", DEVICE_INPUT_CANONICAL]

    def test_seed_text_colours_are_legible_on_white(self):
        for _, info in SEED_MODIFIER_KEYS:
            assert contrast_ratio(info.style.resolved_text_colour, "#FFFFFF") >= 4.5

    def test_seed_aliases_are_normalised_unique_and_point_at_seed_groups(self):
        canonicals = {info.canonical for _, info in SEED_MODIFIER_KEYS}
        names = [alias.alias for _, alias in SEED_ALIASES]
        assert len(names) == len(set(names))
        for _, alias in SEED_ALIASES:
            assert alias.alias == alias.alias.casefold()
            assert alias.canonical in canonicals
            assert alias.kind is ModifierKind.KEY

    def test_side_aliases_are_flagged_and_labelled(self):
        rows = {alias.alias: alias for _, alias in SEED_ALIASES}
        assert rows["lshift"].side_alias is True
        assert rows["lshift"].display_label == "L Shift"
        assert rows["rctrl"].display_label == "R Ctrl"
        assert rows["left alt"].display_label == "L Alt"
        assert rows["control"].side_alias is False
        assert rows["meta"].canonical == "Win"
        # The canonical spelling resolves by name match, not by an alias row
        assert "shift" not in rows
        assert "bms dx shift" not in rows  # BMS keys are discovered, not pre-aliased


# ── Resolution ────────────────────────────────────────────────────────


class TestCanonicalOf:
    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("LShift", "Shift"),
            ("RCtrl", "Ctrl"),
            ("LAlt", "Alt"),
            ("LWin", "Win"),
            ("lalt", "Alt"),
            ("control", "Ctrl"),
            ("SHIFT", "Shift"),
            ("  Right   Shift ", "Shift"),
        ],
    )
    def test_known_spellings(self, raw, canonical):
        assert canonical_of(raw, snap()) == (ModifierKind.KEY, canonical)

    def test_device_inputs_share_the_device_group(self):
        assert canonical_of("JOY_BTN3", snap()) == (
            ModifierKind.KEY,
            DEVICE_INPUT_CANONICAL,
        )
        assert canonical_of("BUTTON_5", snap()) == (
            ModifierKind.KEY,
            DEVICE_INPUT_CANONICAL,
        )

    def test_unknown_key_is_its_own_identity(self):
        assert canonical_of("BMS DX Shift", snap()) == (
            ModifierKind.KEY,
            "BMS DX Shift",
        )

    def test_qualifiers_are_never_aliased(self):
        assert canonical_of("Shift", snap(), ModifierKind.QUALIFIER) == (
            ModifierKind.QUALIFIER,
            "Shift",
        )
        assert canonical_of("lshift", snap(), ModifierKind.QUALIFIER) == (
            ModifierKind.QUALIFIER,
            "lshift",
        )

    def test_key_shift_and_qualifier_shift_are_distinct_identities(self):
        key = canonical_of("Shift", snap(), ModifierKind.KEY)
        qualifier = canonical_of("Shift", snap(), ModifierKind.QUALIFIER)
        assert key != qualifier
        assert snap().group(*key) is not None
        assert snap().group(*qualifier) is None

    def test_sides_toggle_is_applied_at_read_time(self):
        merged = snap(sides_merged=True)
        separate = snap(sides_merged=False)
        assert canonical_of("LShift", merged) == (ModifierKind.KEY, "Shift")
        assert canonical_of("LShift", separate) == (ModifierKind.KEY, "LShift")
        # Non-side aliases and canonical matches still work with the toggle off
        assert canonical_of("shift", separate) == (ModifierKind.KEY, "Shift")
        assert canonical_of("control", separate) == (ModifierKind.KEY, "Ctrl")
        # Nothing was deleted: the alias row is still in the snapshot
        assert "lshift" in separate.aliases

    def test_canonical_keys_follow_built_in_rank(self):
        mod = Modifier({"LShift", "LCtrl", "JOY_BTN3"}, "x")
        assert canonical_keys(mod, snap()) == (
            (ModifierKind.KEY, "Ctrl"),
            (ModifierKind.KEY, "Shift"),
            (ModifierKind.KEY, DEVICE_INPUT_CANONICAL),
        )


class TestResolveKey:
    def test_original_display_keeps_raw_text(self):
        resolved = resolve_key("LShift", snap())
        assert resolved.display_label == "LShift"
        assert resolved.canonical == "Shift"
        assert resolved.group is ModifierKeyGroup.KEYBOARD
        assert resolved.side == "L"
        assert resolved.priority == 30

    def test_simplified_display_keeps_the_side(self):
        s = snap(key_display=ModifierKeyDisplay.SIMPLIFIED)
        assert resolve_key("LShift", s).display_label == "L Shift"
        assert resolve_key("RCtrl", s).display_label == "R Ctrl"
        assert resolve_key("lalt", s).display_label == "L Alt"
        assert resolve_key("shift", s).display_label == "Shift"
        assert resolve_key("control", s).display_label == "Ctrl"

    def test_simplified_display_never_renames_device_inputs_or_unknowns(self):
        s = snap(key_display=ModifierKeyDisplay.SIMPLIFIED)
        assert resolve_key("JOY_BTN3", s).display_label == "JOY_BTN3"
        assert resolve_key("BMS DX Shift", s).display_label == "BMS DX Shift"

    def test_simplified_display_with_sides_off_shows_raw(self):
        s = snap(key_display=ModifierKeyDisplay.SIMPLIFIED, sides_merged=False)
        assert resolve_key("LShift", s).display_label == "LShift"

    def test_side_alias_without_label_synthesises_side_plus_group_label(self):
        custom = ModifierRegistrySnapshot(
            groups={
                (ModifierKind.KEY, "Shift"): ModifierKeyInfo(
                    ModifierKind.KEY, "Shift", "Shift", 30
                )
            },
            aliases={"lshift": ModifierKeyAlias("lshift", "Shift", side_alias=True)},
            key_display=ModifierKeyDisplay.SIMPLIFIED,
        )
        assert resolve_key("LShift", custom).display_label == "L Shift"

    def test_colour_only_when_master_toggle_is_on(self):
        off = resolve_key("LShift", snap(colouring_enabled=False))
        assert off.colour is None
        assert off.text_colour is None
        assert off.style is not None  # the registry style is still exposed for the UI
        on = resolve_key("LShift", snap(colouring_enabled=True))
        assert on.colour == "#0072B2"
        assert on.text_colour == "#005B8E"

    def test_device_inputs_share_one_group_style(self):
        s = snap(colouring_enabled=True)
        assert resolve_key("JOY_BTN3", s).colour == "#56B4E9"
        assert resolve_key("BUTTON_108", s).colour == "#56B4E9"
        assert resolve_key("JOY_BTN3", s).group is ModifierKeyGroup.DEVICE_INPUT

    def test_qualifiers_are_never_coloured(self):
        resolved = resolve_key(
            "Shift", snap(colouring_enabled=True), ModifierKind.QUALIFIER
        )
        assert resolved.colour is None
        assert resolved.style is None
        assert resolved.group is ModifierKeyGroup.QUALIFIER
        assert resolved.priority == mi.QUALIFIER_PRIORITY

    def test_unknown_key_has_default_priority_and_no_colour(self):
        resolved = resolve_key("BMS DX Shift", snap(colouring_enabled=True))
        assert resolved.colour is None
        assert resolved.priority == mi.UNKNOWN_KEY_PRIORITY
        assert resolved.identity == (ModifierKind.KEY, "BMS DX Shift")


class TestResolveCombo:
    def test_highest_priority_key_gives_the_colour(self):
        s = snap(colouring_enabled=True)
        resolved = resolve_keys({"LShift", "LCtrl"}, s)
        assert [k.raw for k in resolved.keys] == ["LCtrl", "LShift"]
        assert resolved.primary.canonical == "Ctrl"
        assert resolved.colour == "#D55E00"
        assert resolved.text_colour == "#A84300"
        assert resolved.text == "LCtrl+LShift"
        assert resolved.identities == (
            (ModifierKind.KEY, "Ctrl"),
            (ModifierKind.KEY, "Shift"),
        )

    def test_text_uses_display_labels_under_simplified(self):
        s = snap(colouring_enabled=True, key_display=ModifierKeyDisplay.SIMPLIFIED)
        assert resolve_keys({"LShift", "LCtrl"}, s).text == "L Ctrl+L Shift"

    def test_unknown_keys_sort_after_known_and_do_not_steal_colour(self):
        s = snap(colouring_enabled=True)
        resolved = resolve_keys({"BMS DX Shift", "LShift"}, s)
        assert [k.raw for k in resolved.keys] == ["LShift", "BMS DX Shift"]
        assert resolved.colour == "#0072B2"
        assert resolved.groups == (ModifierKeyGroup.KEYBOARD,)

    def test_resolve_modifier_uses_the_modifier_kind(self):
        s = snap(colouring_enabled=True)
        qualifier = Modifier(
            {"Shift"}, "cmd", kind=ModifierKind.QUALIFIER, source="profile"
        )
        assert resolve_modifier(qualifier, s).colour is None
        assert resolve_modifier(Modifier({"Shift"}, "cmd"), s).colour == "#0072B2"

    def test_no_colour_when_master_toggle_off(self):
        resolved = resolve_modifier(Modifier({"LShift", "LCtrl"}, "cmd"), snap())
        assert resolved.colour is None
        assert resolved.primary is None
        assert resolved.text == "LCtrl+LShift"

    def test_combo_style_ignores_toggle_and_qualifiers(self):
        s = snap()
        style = combo_style(
            [
                (ModifierKind.QUALIFIER, "Ctrl"),
                (ModifierKind.KEY, "Shift"),
                (ModifierKind.KEY, "Alt"),
            ],
            s,
        )
        assert style is not None and style.colour == "#009E73"
        assert combo_style([(ModifierKind.QUALIFIER, "Long")], s) is None
        assert combo_style([(ModifierKind.KEY, "Unknown")], s) is None


# ── Colour helpers and style ──────────────────────────────────────────


class TestColours:
    def test_contrast_ratio_extremes(self):
        assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
        assert contrast_ratio("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)
        assert contrast_ratio("#0072B2", "#FFFFFF") == pytest.approx(5.19, abs=0.01)

    def test_text_safe_colour_darkens_until_legible(self):
        safe = text_safe_colour("#56B4E9")
        assert contrast_ratio(safe, "#FFFFFF") >= 4.5
        assert safe != "#56B4E9"
        assert text_safe_colour("#005B8E") == "#005B8E"  # already fine, unchanged

    def test_text_safe_colour_lightens_on_dark_backgrounds(self):
        safe = text_safe_colour("#1A1A40", background="#000000")
        assert contrast_ratio(safe, "#000000") >= 4.5

    def test_style_json_round_trip_and_validation(self):
        style = ModifierKeyStyle("#0072B2", "#005B8E")
        assert ModifierKeyStyle.from_json(style.to_json()) == style
        assert ModifierKeyStyle.from_json(None) is None
        assert ModifierKeyStyle.from_json("not json") is None
        assert ModifierKeyStyle("#56B4E9").resolved_text_colour == "#3C7DA3"
        with pytest.raises(ValueError):
            ModifierKeyStyle("blue")


# ── Snapshot ──────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_mappings_are_read_only_copies(self):
        source_groups = {info.key: info for _, info in SEED_MODIFIER_KEYS}
        s = ModifierRegistrySnapshot(groups=source_groups, aliases={})
        source_groups.clear()
        assert len(s.groups) == len(SEED_MODIFIER_KEYS)
        with pytest.raises(TypeError):
            s.groups[(ModifierKind.KEY, "X")] = None  # type: ignore[index]

    def test_group_by_name_is_case_insensitive_and_key_only(self):
        s = snap()
        assert s.group_by_name("shift").canonical == "Shift"
        assert s.group_by_name("  SHIFT ").canonical == "Shift"
        assert s.group_by_name("nothing") is None


# ── Discovery ─────────────────────────────────────────────────────────


def _wrapper(plugin: str, profile: Profile_):
    wrapper = MagicMock()
    wrapper.profile = profile
    wrapper.profile_origin.name = plugin
    return wrapper


class TestDiscovery:
    def test_counts_per_plugin_kind_and_source(self):
        dcs = Profile_("dcs")
        stick = dcs.add_device(GUID, "Stick")
        stick.add_modifier_to_input(Button(1), {"LShift"}, "a")
        stick.add_modifier_to_input(Button(2), {"LShift", "LCtrl"}, "b")
        stick.get_input("buttons", "BUTTON_2").modifiers.append(
            Modifier({"Long"}, "c", kind=ModifierKind.QUALIFIER, source="route")
        )
        sc = Profile_("sc")
        sc.add_device(GUID, "Stick").add_modifier_to_input(Button(1), {"lalt"}, "d")
        sc.devices[GUID].add_modifier_to_input(Button(3), {"LShift"}, "e")

        found = discover_modifier_keys(
            [_wrapper("DCS World", dcs), _wrapper("Star Citizen", sc)]
        )

        by_identity = {d.identity: d for d in found}
        shift = by_identity[(ModifierKind.KEY, "LShift")]
        assert shift.count == 3
        assert shift.plugins == {"DCS World": 2, "Star Citizen": 1}
        assert shift.group is ModifierKeyGroup.KEYBOARD
        assert by_identity[(ModifierKind.KEY, "LCtrl")].count == 1
        assert by_identity[(ModifierKind.KEY, "lalt")].plugins == {"Star Citizen": 1}
        long = by_identity[(ModifierKind.QUALIFIER, "Long")]
        assert long.sources == {"route"}
        assert long.group is ModifierKeyGroup.QUALIFIER
        # Sorted by count desc, then kind, then raw
        assert found[0] is shift

    def test_wrappers_without_profiles_are_skipped(self):
        empty = MagicMock()
        empty.profile = None
        assert discover_modifier_keys([empty]) == []
