"""Tests for the shared local-source install flow.

The point of extracting this flow is that the manual (settings/ZIP) route and the
catalog-driven store apply *identical* security handling, so the trust calls are
asserted here, not just patched out.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.db import db_plugin_data  # noqa: E402
from joystick_diagrams.ui import plugin_install_flow as flow  # noqa: E402


def _app_state():
    return MagicMock()


def _reload_writes_config_row(_app_state_arg, _plugin_type):
    """Stand-in for the real reload's side effect on the configuration table.

    ``reload_plugin_manager`` -> ``create_plugin_wrappers()`` -> ``PluginWrapper``
    ``.setup_plugin()`` inserts a row for any plugin that lacks one. Reproducing that
    here is what lets these tests catch the "is this plugin new?" check being sampled
    *after* the reload, where every plugin looks pre-existing.
    """
    db_plugin_data.add__update_plugin_configuration("My Plugin", False)


@pytest.mark.uitest
def test_returns_plugin_name_on_success(qapp, tmp_path):
    installed = tmp_path / "my_plugin"
    installed.mkdir()
    state = _app_state()

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Plugin"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True) as mock_record,
        patch.object(flow, "reload_plugin_manager", autospec=True) as mock_reload,
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), state, None)

    assert result == "My Plugin"
    mock_record.assert_called_once_with("My Plugin", "parser", installed)
    mock_reload.assert_called_once_with(state, "parser")


@pytest.mark.uitest
def test_records_trust_for_the_requested_plugin_type(qapp, tmp_path):
    installed = tmp_path / "my_plugin"
    installed.mkdir()
    state = _app_state()

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Exporter"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True) as mock_record,
        patch.object(flow, "reload_plugin_manager", autospec=True) as mock_reload,
    ):
        flow.install_from_local_source(Path("plugin.zip"), state, None, "output")

    mock_record.assert_called_once_with("My Exporter", "output", installed)
    mock_reload.assert_called_once_with(state, "output")


@pytest.mark.uitest
def test_returns_none_and_removes_plugin_when_trust_declined(qapp, tmp_path):
    installed = tmp_path / "my_plugin"
    installed.mkdir()

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Plugin"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=False),
        patch.object(flow, "record_trust", autospec=True) as mock_record,
        patch.object(flow, "reload_plugin_manager", autospec=True) as mock_reload,
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), _app_state(), None)

    assert result is None
    assert not installed.exists()
    mock_record.assert_not_called()
    mock_reload.assert_not_called()


@pytest.mark.uitest
def test_returns_none_when_installer_raises(qapp):
    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            side_effect=OSError("bad zip"),
        ),
        patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning,
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), _app_state(), None)

    assert result is None
    mock_warning.assert_called_once_with(None, "Install Failed", "bad zip")


@pytest.mark.uitest
def test_enables_the_newly_installed_plugin(qapp, tmp_path):
    """Picking a plugin is a statement of intent — it must not land disabled.

    The reload mock writes a configuration row exactly as the real one does, so this
    also pins the "is it new?" check to *before* the reload.
    """
    installed = tmp_path / "my_plugin"
    installed.mkdir()
    wrapper = SimpleNamespace(name="My Plugin", enabled=False)
    state = _app_state()
    state.plugin_manager.plugin_wrappers = [wrapper]
    assert db_plugin_data.get_plugin_configuration("My Plugin") is None

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Plugin"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(
            flow,
            "reload_plugin_manager",
            autospec=True,
            side_effect=_reload_writes_config_row,
        ),
    ):
        flow.install_from_local_source(Path("plugin.zip"), state, None)

    assert wrapper.enabled is True


@pytest.mark.uitest
def test_reinstall_does_not_re_enable_a_deliberately_disabled_plugin(qapp, tmp_path):
    """Uninstall promises "Plugin settings will be preserved".

    Reinstalling over a plugin the user had switched off must honour that rather than
    resurrecting it — the configuration row survives uninstall by design.
    """
    installed = tmp_path / "my_plugin"
    installed.mkdir()
    db_plugin_data.add__update_plugin_configuration("My Plugin", False)
    wrapper = SimpleNamespace(name="My Plugin", enabled=False)
    state = _app_state()
    state.plugin_manager.plugin_wrappers = [wrapper]

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Plugin"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), state, None)

    assert result == "My Plugin"
    assert wrapper.enabled is False
    assert db_plugin_data.get_plugin_configuration("My Plugin") == ("My Plugin", 0)


@pytest.mark.uitest
def test_install_still_succeeds_when_the_new_wrapper_cannot_be_found(qapp, tmp_path):
    """A reload that does not surface the plugin must not turn a success into a crash."""
    installed = tmp_path / "my_plugin"
    installed.mkdir()
    state = _app_state()
    state.plugin_manager.plugin_wrappers = []

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "My Plugin"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
    ):
        result = flow.install_from_local_source(Path("plugin.zip"), state, None)

    assert result == "My Plugin"
