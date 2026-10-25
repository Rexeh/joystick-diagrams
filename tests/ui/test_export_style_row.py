"""The Export page's Style row and the one-time styles banner."""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QPushButton  # noqa: E402

from joystick_diagrams.render.theme import (  # noqa: E402
    ACTIVE_THEME_SETTING_KEY,
    ORIGINAL_THEME_NAME,
    TEMPLATE_ORIGINAL_THEME_ID,
)
from joystick_diagrams.ui import strings_appearance as S  # noqa: E402
from joystick_diagrams.ui.export_page import (  # noqa: E402
    WHATS_NEW_STYLES_DISMISSED_SETTING_KEY,
    ExportPage,
)
from joystick_diagrams.ui.export_settings import ExportSettings  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_app_state():
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


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


def _seed_app_state():
    from joystick_diagrams.app_state import AppState

    manager = MagicMock()
    manager.plugin_wrappers = []
    manager.get_enabled_plugin_wrappers.return_value = []
    output = MagicMock()
    output.get_enabled_plugin_wrappers.return_value = []
    return AppState(plugin_manager=manager, output_plugin_manager=output)


@pytest.mark.uitest
def test_style_combo_lists_styles_and_sets_active(qapp, settings_store):
    state = _seed_app_state()
    widget = ExportSettings()

    names = [
        widget.export_style.itemText(i) for i in range(widget.export_style.count())
    ]
    assert names[:4] == [
        ORIGINAL_THEME_NAME,
        "Clean",
        "Print friendly",
        "High contrast",
    ]
    assert widget.get_style_id() == TEMPLATE_ORIGINAL_THEME_ID
    assert widget.edit_style_button.text() == S.EXPORT_STYLE_EDIT

    widget.export_style.setCurrentIndex(widget.export_style.findData("high_contrast"))
    assert settings_store[ACTIVE_THEME_SETTING_KEY] == "high_contrast"
    assert state.theme_service.active_theme_id() == "high_contrast"

    state.theme_service.set_active("clean")
    widget.refresh_style_combo()
    assert widget.get_style_id() == "clean"


@pytest.mark.uitest
def test_whats_new_banner_shows_once(qapp, settings_store):
    _seed_app_state()
    page = ExportPage()
    assert page._whats_new_banner is not None
    dismiss = next(
        b
        for b in page._whats_new_banner.findChildren(QPushButton)
        if b.text() == S.WHATS_NEW_DISMISS
    )
    dismiss.click()
    assert settings_store[WHATS_NEW_STYLES_DISMISSED_SETTING_KEY] == "true"
    assert page._whats_new_banner is None

    again = ExportPage()
    assert again._whats_new_banner is None
