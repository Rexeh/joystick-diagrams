"""The "Showing modifiers" setting: migration from the legacy checkbox and write-back."""

from unittest.mock import patch

import pytest

from joystick_diagrams.export import (
    MERGE_MODIFIERS_SETTING_KEY,
    merge_modifiers_enabled,
)
from joystick_diagrams.modifier_identity import (
    LEGACY_MERGE_MODIFIERS_SETTING_KEY,
    MODIFIER_DISPLAY_SETTING_KEY,
    ModifierDisplay,
    get_modifier_display,
    modifiers_in_main_text,
    set_modifier_display,
)


@pytest.fixture
def store():
    """A dict-backed settings table so reads see earlier writes."""
    values: dict[str, str] = {}
    with (
        patch("joystick_diagrams.db.db_settings.get_setting", side_effect=values.get),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value",
            side_effect=values.__setitem__,
        ),
    ):
        yield values


def test_legacy_key_constant_is_the_old_checkbox_key():
    assert (
        MERGE_MODIFIERS_SETTING_KEY
        == LEGACY_MERGE_MODIFIERS_SETTING_KEY
        == "merge_modifiers_into_input"
    )


def test_default_is_template_boxes(store):
    assert get_modifier_display() is ModifierDisplay.TEMPLATE_BOXES
    assert merge_modifiers_enabled() is False


def test_legacy_true_migrates_to_merged_same_line(store):
    store[LEGACY_MERGE_MODIFIERS_SETTING_KEY] = "true"
    assert get_modifier_display() is ModifierDisplay.MERGED_SAME_LINE
    assert merge_modifiers_enabled() is True
    store[LEGACY_MERGE_MODIFIERS_SETTING_KEY] = "false"
    assert get_modifier_display() is ModifierDisplay.TEMPLATE_BOXES


def test_new_key_wins_over_legacy_and_invalid_values_fall_back(store):
    store[LEGACY_MERGE_MODIFIERS_SETTING_KEY] = "true"
    store[MODIFIER_DISPLAY_SETTING_KEY] = "TEMPLATE_BOXES"
    assert get_modifier_display() is ModifierDisplay.TEMPLATE_BOXES
    store[MODIFIER_DISPLAY_SETTING_KEY] = "garbage"
    assert get_modifier_display() is ModifierDisplay.MERGED_SAME_LINE


@pytest.mark.parametrize(
    ("display", "legacy"),
    [
        (ModifierDisplay.TEMPLATE_BOXES, "false"),
        (ModifierDisplay.UNDER_MAIN_TEXT, "true"),
        (ModifierDisplay.MERGED_SAME_LINE, "true"),
    ],
)
def test_set_writes_both_keys_for_downgrade_safety(store, display, legacy):
    set_modifier_display(display)
    assert store[MODIFIER_DISPLAY_SETTING_KEY] == display.value
    assert store[LEGACY_MERGE_MODIFIERS_SETTING_KEY] == legacy
    assert get_modifier_display() is display
    assert merge_modifiers_enabled() is modifiers_in_main_text(display)
