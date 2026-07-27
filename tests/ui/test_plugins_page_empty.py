"""Tests for the Plugin Setup page's zero-plugin branch."""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.ui.plugins_page import PluginsPage  # noqa: E402
from joystick_diagrams.ui.widgets.plugin_empty_state import (  # noqa: E402
    PluginEmptyState,
)


def _wrapper(name="DCS World", ready=True):
    wrapper = MagicMock()
    wrapper.name = name
    wrapper.ready = ready
    wrapper.enabled = True
    wrapper.error = None
    wrapper.version = "2.0.0"
    wrapper.icon = ""
    wrapper.plugin_profile_collection = None
    return wrapper


@pytest.fixture(autouse=True)
def _reset_app_state():
    """AppState is a seeded singleton — reset it so each test can supply its own manager."""
    from joystick_diagrams.app_state import AppState

    AppState._inst = None
    yield
    AppState._inst = None


def _page(qapp, wrappers):
    """Build a PluginsPage whose plugin manager reports the given wrappers.

    AppState must be seeded *before* PluginsPage() because __init__ reads
    plugin_wrappers (for the guidance banner) and calls populate_plugin_cards().
    The catalog fetch is patched out for the same reason — construction must not
    hit the network.
    """
    from joystick_diagrams.app_state import AppState

    manager = MagicMock()
    manager.plugin_wrappers = wrappers
    manager.is_user_plugin.return_value = False
    AppState(plugin_manager=manager, output_plugin_manager=MagicMock())

    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        return PluginsPage()


@pytest.mark.uitest
def test_zero_plugins_renders_empty_state(qapp):
    page = _page(qapp, [])

    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()

    assert isinstance(page._empty_state, PluginEmptyState)
    assert page._plugin_cards == []


@pytest.mark.uitest
def test_installed_plugins_render_cards_not_empty_state(qapp):
    page = _page(qapp, [_wrapper()])

    page.populate_plugin_cards()

    assert page._empty_state is None
    assert len(page._plugin_cards) == 1


@pytest.mark.uitest
def test_run_button_hidden_when_no_plugins(qapp):
    page = _page(qapp, [])

    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()

    assert page.runPluginsButton.isVisibleTo(page) is False


@pytest.mark.uitest
def test_run_button_visible_when_plugins_present(qapp):
    page = _page(qapp, [_wrapper()])

    page.populate_plugin_cards()

    assert page.runPluginsButton.isVisibleTo(page) is True


@pytest.mark.uitest
def test_unreachable_catalog_shows_unavailable_state(qapp):
    page = _page(qapp, [])

    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()
    page._on_empty_state_catalog(None)

    from PySide6.QtWidgets import QPushButton

    texts = {b.text() for b in page._empty_state.findChildren(QPushButton)}
    assert "Retry" in texts
    assert "Install from ZIP..." in texts


@pytest.mark.uitest
def test_empty_state_cleared_when_plugins_appear(qapp):
    page = _page(qapp, [])
    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()
    assert page._empty_state is not None

    page.appState.plugin_manager.plugin_wrappers = [_wrapper()]
    page.populate_plugin_cards()

    assert page._empty_state is None
    assert len(page._plugin_cards) == 1


@pytest.mark.uitest
def test_nudge_appears_for_first_unconfigured_plugin(qapp):
    page = _page(qapp, [_wrapper("DCS World", ready=False)])

    page.populate_plugin_cards()

    assert page._config_nudge is not None
    from PySide6.QtWidgets import QLabel

    texts = {label.text() for label in page._config_nudge.findChildren(QLabel)}
    assert "DCS World needs a path before it can run." in texts


@pytest.mark.uitest
def test_nudge_absent_when_every_plugin_is_ready(qapp):
    page = _page(qapp, [_wrapper("DCS World", ready=True)])

    page.populate_plugin_cards()

    assert page._config_nudge is None


@pytest.mark.uitest
def test_nudge_clears_once_plugin_becomes_ready(qapp):
    from PySide6.QtWidgets import QLabel

    wrapper = _wrapper("DCS World", ready=False)
    page = _page(qapp, [wrapper])
    page.populate_plugin_cards()
    assert page._config_nudge is not None

    nudge_text = "DCS World needs a path before it can run."
    assert nudge_text in {label.text() for label in page.findChildren(QLabel)}

    wrapper.ready = True
    page._on_settings_changed()

    assert page._config_nudge is None
    # Guards against a regression where the banner is nulled out but never
    # actually reparented/torn down (findChildren scoped to the page, not the
    # banner, so a dangling-but-unparented widget would still be found here).
    assert nudge_text not in {label.text() for label in page.findChildren(QLabel)}


@pytest.mark.uitest
def test_no_nudge_when_no_plugins_installed(qapp):
    page = _page(qapp, [])

    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()

    assert page._config_nudge is None
