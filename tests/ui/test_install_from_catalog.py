"""Tests for the catalog-driven install flow.

Covers the behaviour the store and the first-run picker share: a plugin the user
deliberately chose must come back enabled, a plugin that cannot be located after
the manager reload must not turn a successful install into a crash, and — because
this same function is the store's *update* path — a plugin the user has already
made a choice about must keep that choice.

These tests use the real configuration table (via the autouse ``temp_database``
fixture) rather than patching the lookup, so the actual query is what is verified.
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.db import db_plugin_data  # noqa: E402
from joystick_diagrams.output_plugin_wrapper import _DB_PREFIX  # noqa: E402
from joystick_diagrams.plugins import plugin_catalog as pc  # noqa: E402
from joystick_diagrams.ui import plugin_install_flow as flow  # noqa: E402

PLUGIN_NAME = "DCS World"
OUTPUT_KEY = f"{_DB_PREFIX}{PLUGIN_NAME}"


def _entry(plugin_type="parser"):
    return pc.CatalogEntry(
        id=str(uuid4()),
        name=PLUGIN_NAME,
        type=plugin_type,
        version="1.0.0",
        download_url="https://example.com/p.zip",
        sha256="0" * 64,
    )


def _app_state():
    state = MagicMock()
    state.plugin_manager.plugin_wrappers = []
    state.output_plugin_manager.plugin_wrappers = []
    return state


def _reload_writes_config_row(_app_state_arg, plugin_type):
    """Stand-in for the real reload's side effect on the configuration table.

    ``reload_plugin_manager`` -> ``create_plugin_wrappers()`` -> ``setup_plugin()``
    inserts a row for any plugin that lacks one. Reproducing that here is what makes
    these tests able to catch the "is this plugin new?" check being sampled *after*
    the reload, where every plugin looks pre-existing.

    Keyed per type, exactly as the wrappers do: parsers under the bare name,
    output plugins under ``output:<name>``.
    """
    key = PLUGIN_NAME if plugin_type == "parser" else OUTPUT_KEY
    db_plugin_data.add__update_plugin_configuration(key, False)


@pytest.mark.uitest
def test_enables_the_newly_installed_plugin(qapp, tmp_path):
    """A plugin with no stored choice is new, so installing it enables it.

    The reload mock writes a configuration row exactly as the real one does, so this
    also pins the "is it new?" check to *before* the reload — sampled after, the row
    it just wrote would make every plugin look pre-existing.
    """
    installed = tmp_path / "dcs_world"
    installed.mkdir()
    wrapper = SimpleNamespace(name=PLUGIN_NAME, enabled=False)
    state = _app_state()
    state.plugin_manager.plugin_wrappers = [wrapper]
    assert db_plugin_data.get_plugin_configuration(PLUGIN_NAME) is None

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, PLUGIN_NAME),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True) as mock_record,
        patch.object(
            flow,
            "reload_plugin_manager",
            autospec=True,
            side_effect=_reload_writes_config_row,
        ) as mock_reload,
    ):
        result = flow.install_from_catalog(_entry(), state, None)

    assert result == PLUGIN_NAME
    assert wrapper.enabled is True
    mock_record.assert_called_once_with(PLUGIN_NAME, "parser", installed)
    mock_reload.assert_called_once_with(state, "parser")


@pytest.mark.uitest
def test_update_does_not_re_enable_a_deliberately_disabled_plugin(qapp, tmp_path):
    """install_from_catalog is also the store's update path.

    A user who disabled DCS World and later clicks "Update -> v2.1.0" must not have it
    silently switched back on and run on the next Run.
    """
    installed = tmp_path / "dcs_world"
    installed.mkdir()
    db_plugin_data.add__update_plugin_configuration(PLUGIN_NAME, False)
    wrapper = SimpleNamespace(name=PLUGIN_NAME, enabled=False)
    state = _app_state()
    state.plugin_manager.plugin_wrappers = [wrapper]

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, PLUGIN_NAME),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
    ):
        result = flow.install_from_catalog(_entry(), state, None)

    assert result == PLUGIN_NAME
    assert wrapper.enabled is False
    assert db_plugin_data.get_plugin_configuration(PLUGIN_NAME) == (PLUGIN_NAME, 0)


@pytest.mark.uitest
def test_update_leaves_a_plugin_with_a_stored_choice_untouched(qapp, tmp_path):
    """An existing choice means the flow declines to interfere at all.

    Asserting on ``enabled`` alone would be tautological here — seeding True and
    asserting True passes whether the flow enables, skips, or does nothing. So this
    asserts the enable is never *attempted*, which is the actual invariant and fails
    the moment the skip is dropped.
    """
    installed = tmp_path / "dcs_world"
    installed.mkdir()
    db_plugin_data.add__update_plugin_configuration(PLUGIN_NAME, True)
    wrapper = SimpleNamespace(name=PLUGIN_NAME, enabled=True)
    state = _app_state()
    state.plugin_manager.plugin_wrappers = [wrapper]

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, PLUGIN_NAME),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
        patch.object(flow, "enable_installed_plugin", autospec=True) as mock_enable,
    ):
        flow.install_from_catalog(_entry(), state, None)

    mock_enable.assert_not_called()
    assert wrapper.enabled is True


@pytest.mark.uitest
def test_output_plugin_is_enabled_on_the_output_manager(qapp, tmp_path):
    """A new output plugin is enabled, and the reload writes the prefixed key.

    This previously passed for the wrong reason: with a bare-name lookup an output
    plugin's row could never be seen, so every output install looked new whatever the
    check did. The reload mock now writes ``output:<name>`` as the real wrapper does.
    """
    installed = tmp_path / "exporter"
    installed.mkdir()
    wrapper = SimpleNamespace(name=PLUGIN_NAME, enabled=False)
    state = _app_state()
    state.output_plugin_manager.plugin_wrappers = [wrapper]
    assert db_plugin_data.get_plugin_configuration(OUTPUT_KEY) is None

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, PLUGIN_NAME),
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
        flow.install_from_catalog(_entry("output"), state, None)

    assert wrapper.enabled is True


@pytest.mark.uitest
def test_output_update_does_not_re_enable_a_disabled_plugin(qapp, tmp_path):
    """The parser fix must hold for output plugins too.

    OpenKneeboard ships in the live catalog as type "output", is disableable in
    Settings, and export runs only get_enabled_plugin_wrappers() — so silently
    re-enabling it on update means it starts exporting again unasked.
    """
    installed = tmp_path / "exporter"
    installed.mkdir()
    db_plugin_data.add__update_plugin_configuration(OUTPUT_KEY, False)
    wrapper = SimpleNamespace(name=PLUGIN_NAME, enabled=False)
    state = _app_state()
    state.output_plugin_manager.plugin_wrappers = [wrapper]

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, PLUGIN_NAME),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
    ):
        result = flow.install_from_catalog(_entry("output"), state, None)

    assert result == PLUGIN_NAME
    assert wrapper.enabled is False
    assert db_plugin_data.get_plugin_configuration(OUTPUT_KEY) == (OUTPUT_KEY, 0)


@pytest.mark.uitest
def test_new_output_plugin_is_not_blocked_by_a_parser_row_of_the_same_name(
    qapp, tmp_path
):
    """The mirror failure of a bare-name lookup.

    A parser row under the same bare name must not make a genuinely new output plugin
    look pre-existing — that would leave it disabled, reinstating the dead-end the
    auto-enable exists to remove. The two types are namespaced apart in the table.
    """
    installed = tmp_path / "exporter"
    installed.mkdir()
    db_plugin_data.add__update_plugin_configuration(PLUGIN_NAME, False)  # parser row
    wrapper = SimpleNamespace(name=PLUGIN_NAME, enabled=False)
    state = _app_state()
    state.output_plugin_manager.plugin_wrappers = [wrapper]

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, PLUGIN_NAME),
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
        flow.install_from_catalog(_entry("output"), state, None)

    assert wrapper.enabled is True
    # The parser's own choice is untouched by the output install.
    assert db_plugin_data.get_plugin_configuration(PLUGIN_NAME) == (PLUGIN_NAME, 0)


@pytest.mark.uitest
def test_install_still_succeeds_when_the_new_wrapper_cannot_be_found(qapp, tmp_path):
    installed = tmp_path / "dcs_world"
    installed.mkdir()
    state = _app_state()

    with (
        patch(
            "joystick_diagrams.plugins.plugin_installer.install_plugin",
            return_value=installed,
        ),
        patch(
            "joystick_diagrams.plugins.plugin_installer.validate_plugin",
            return_value=(True, "DCS World"),
        ),
        patch.object(flow, "run_security_check", autospec=True, return_value=True),
        patch.object(flow, "record_trust", autospec=True),
        patch.object(flow, "reload_plugin_manager", autospec=True),
    ):
        result = flow.install_from_catalog(_entry(), state, None)

    assert result == "DCS World"
