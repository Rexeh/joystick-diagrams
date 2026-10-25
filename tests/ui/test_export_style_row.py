"""The Export page's Style row and the one-time styles banner."""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.render.theme import (  # noqa: E402
    ORIGINAL_THEME_NAME,
    TEMPLATE_ORIGINAL_THEME_ID,
)
from joystick_diagrams.ui import strings_diagrams as S  # noqa: E402
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


def _seed_app_state(output_wrappers=()):
    from joystick_diagrams.app_state import AppState

    manager = MagicMock()
    manager.plugin_wrappers = []
    manager.get_enabled_plugin_wrappers.return_value = []
    output = MagicMock()
    output.get_enabled_plugin_wrappers.return_value = list(output_wrappers)
    return AppState(plugin_manager=manager, output_plugin_manager=output)


@pytest.mark.uitest
def test_style_row_names_the_active_style_and_change_opens_appearance(
    qapp, settings_store
):
    state = _seed_app_state()
    widget = ExportSettings()
    assert widget.style_label.text() == ORIGINAL_THEME_NAME
    assert widget.get_style_id() == TEMPLATE_ORIGINAL_THEME_ID
    assert widget.change_style_button.text() == S.CHANGE_ELLIPSIS
    requested = []
    widget.style_change_requested.connect(lambda: requested.append(True))
    widget.change_style_button.click()
    assert requested == [True]

    state.theme_service.set_active("clean")
    widget.refresh_style()
    assert widget.get_style_id() == "clean"
    assert widget.style_label.text() == "Clean"


@pytest.mark.uitest
def test_format_save_to_and_other_apps_rows(qapp, settings_store, tmp_path):
    app = MagicMock()
    app.name = "OpenKneeboard"
    app.ready = True
    _seed_app_state([app])
    widget = ExportSettings()
    formats = [
        widget.export_format.itemText(i) for i in range(widget.export_format.count())
    ]
    assert formats == ["SVG", "PNG", "PDF"]
    widget.set_export_format("PDF")
    assert settings_store["export_format"] == "PDF"
    assert widget.folder_label.text() == S.SAVE_TO_UNSET
    assert not widget.change_folder_button.isVisibleTo(widget)
    assert widget.apps_label.text() == "OpenKneeboard · On"
    with patch(
        "joystick_diagrams.ui.export_settings.QFileDialog.getExistingDirectory",
        return_value=str(tmp_path),
    ):
        assert widget.choose_folder() == tmp_path
    assert widget.folder_label.text() == str(tmp_path)
    assert widget.folder_hint.text() == S.SAVE_TO_HINT
