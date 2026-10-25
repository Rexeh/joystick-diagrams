"""Smoke tests for Customise → Appearance (offscreen; the WebEngine preview is never shown)."""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QLabel  # noqa: E402

from joystick_diagrams.input.button import Button  # noqa: E402
from joystick_diagrams.input.modifier import ModifierKind  # noqa: E402
from joystick_diagrams.input.profile import Profile_  # noqa: E402
from joystick_diagrams.modifier_identity import (  # noqa: E402
    MODIFIER_COLOURING_SETTING_KEY,
    MODIFIER_DISPLAY_SETTING_KEY,
    ModifierDisplay,
)
from joystick_diagrams.render.theme import (  # noqa: E402
    ACTIVE_THEME_SETTING_KEY,
    TEMPLATE_ORIGINAL_THEME_ID,
    ThemeRole,
)
from joystick_diagrams.ui import strings_appearance as S  # noqa: E402
from joystick_diagrams.ui.customise_appearance import (  # noqa: E402
    CustomiseAppearance,
    StyleTab,
)

# The migrated throwaway database comes from tests/ui/conftest.py (autouse).


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


@pytest.fixture
def settings_store():
    """Dict-backed settings so the page reads back what it wrote (conftest patches reads to None)."""
    values: dict[str, str] = {}
    with (
        patch("joystick_diagrams.db.db_settings.get_setting", side_effect=values.get),
        patch(
            "joystick_diagrams.db.db_settings.add_update_setting_value",
            side_effect=values.__setitem__,
        ),
    ):
        yield values


def _profile_wrapper():
    profile = Profile_("F-16C")
    device = profile.add_device("666ec0a0-556b-11ee-8002-444553540000", "Stick")
    device.create_input(Button(1), "Fire")
    device.add_modifier_to_input(Button(1), {"LShift"}, "Alt Fire")
    device.add_modifier_to_input(Button(1), {"BMS DX Shift"}, "Other")
    device.add_modifier_to_input(
        Button(1), {"Long"}, "Eject", kind=ModifierKind.QUALIFIER
    )
    wrapper = MagicMock()
    wrapper.profile = profile
    wrapper.profile_origin.name = "DCS World"
    wrapper.profile_name = "F-16c"
    wrapper.profile_key = "dcs world_f-16c"
    return wrapper


def _seed_app_state(profile_wrappers=()):
    from joystick_diagrams.app_state import AppState

    manager = MagicMock()
    manager.plugin_wrappers = []
    manager.get_enabled_plugin_wrappers.return_value = []
    state = AppState(plugin_manager=manager, output_plugin_manager=MagicMock())
    state.profile_wrappers = list(profile_wrappers)
    return state


def _labels(widget) -> set[str]:
    return {label.text() for label in widget.findChildren(QLabel)}


@pytest.mark.uitest
def test_page_opens_with_original_selected_and_sample_preview(qapp, settings_store):
    _seed_app_state()
    page = CustomiseAppearance()

    assert page.tabs.tabText(0) == S.TAB_STYLE
    assert page.tabs.tabText(1) == S.TAB_MODIFIER_KEYS
    tab = page.style_tab
    assert list(tab._cards)[0] == TEMPLATE_ORIGINAL_THEME_ID
    assert tab._cards[TEMPLATE_ORIGINAL_THEME_ID].badge.isVisibleTo(tab)
    assert not tab._editor_form_widget.isEnabled()
    # No controller has a template: the Starter Template with sample bindings
    assert not tab.empty_state.isVisibleTo(tab) and tab.preview.isVisibleTo(tab)
    assert tab.sample_note.isVisibleTo(tab) and not tab.preview_combo.isVisibleTo(tab)
    assert tab._sample is not None and tab._sample.has_template
    assert tab.preview.web_view() is None  # WebEngine never started
    # "Colour by modifier key" is a checkbox on the Style tab too
    tab.colour_by_key.setChecked(True)
    from joystick_diagrams.modifier_identity import modifier_colouring_enabled

    assert modifier_colouring_enabled()


@pytest.mark.uitest
def test_editing_a_builtin_creates_a_copy_and_activates_it(qapp, settings_store):
    state = _seed_app_state()
    tab = StyleTab()

    tab._on_card_clicked("clean")
    assert tab._editor_form_widget.isEnabled()
    tab.size_spin.setValue(11)

    copies = state.theme_service.user_themes()
    assert len(copies) == 1
    copy = copies[0]
    assert copy.name == "My style (based on Clean)"
    assert copy.text(ThemeRole.BOUND).font_size == 11
    assert settings_store[ACTIVE_THEME_SETTING_KEY] == copy.theme_id
    assert tab._selected_id == copy.theme_id
    assert copy.theme_id in tab._cards
    assert tab.preview.is_dirty

    tab.text_colour.set_colour("#123456", emit=True)
    assert (
        state.theme_service.get(copy.theme_id).text(ThemeRole.BOUND).colour == "#123456"
    )
    assert len(state.theme_service.user_themes()) == 1  # edits stay on the copy


@pytest.mark.uitest
def test_use_for_all_exports_and_showing_modifiers_persist(qapp, settings_store):
    state = _seed_app_state()
    tab = StyleTab()

    tab._on_card_clicked("print_friendly")
    assert tab.use_button.isEnabled()
    tab.use_button.click()
    assert state.theme_service.active_theme_id() == "print_friendly"
    assert not tab.use_button.isEnabled()

    tab._display_buttons[ModifierDisplay.UNDER_MAIN_TEXT].setChecked(True)
    assert settings_store[MODIFIER_DISPLAY_SETTING_KEY] == "UNDER_MAIN_TEXT"
    assert settings_store["merge_modifiers_into_input"] == "true"


@pytest.mark.uitest
def test_refresh_does_not_render(qapp, settings_store):
    _seed_app_state()
    page = CustomiseAppearance()
    with patch.object(page.style_tab.preview, "_start_render") as render:
        page.refresh()
        page.show_tab(CustomiseAppearance.TAB_MODIFIER_KEYS)
        page.refresh()
    render.assert_not_called()


@pytest.mark.uitest
def test_modifier_keys_tab_lists_discovered_keys_and_persists_toggles(
    qapp, settings_store
):
    state = _seed_app_state([_profile_wrapper()])
    page = CustomiseAppearance()
    tab = page.modifier_keys_tab

    names = [tab.table.item(row, 2).text() for row in range(tab.table.rowCount())]
    assert names[:4] == ["Ctrl", "Alt", "Shift", "Win"]
    texts = _labels(tab)
    assert any("LShift" in t and "DCS World" in t and "1 bind" in t for t in texts)
    assert any("Long" in t for t in texts)  # qualifier under "Other labels"
    assert any("BMS DX Shift" in t for t in texts)  # ungrouped key listed
    for forbidden in ("alias", "canonical", "Template original"):
        assert not any(forbidden in t for t in texts), forbidden

    tab.master_switch.setChecked(True)
    assert settings_store[MODIFIER_COLOURING_SETTING_KEY] == "true"
    assert page.style_tab.preview.is_dirty

    shift = state.modifier_key_service.get_group(ModifierKind.KEY, "Shift")
    tab._move(shift, -1)
    order = [
        g.canonical
        for g in state.modifier_key_service.get_groups()
        if g.kind is ModifierKind.KEY
    ]
    assert order[:3] == ["Ctrl", "Shift", "Alt"]
