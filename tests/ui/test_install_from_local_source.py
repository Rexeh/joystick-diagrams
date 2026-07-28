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

from joystick_diagrams.ui import plugin_install_flow as flow  # noqa: E402


def _app_state():
    return MagicMock()


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
    """Picking a plugin is a statement of intent — it must not land disabled."""
    installed = tmp_path / "my_plugin"
    installed.mkdir()
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
        flow.install_from_local_source(Path("plugin.zip"), state, None)

    assert wrapper.enabled is True


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
