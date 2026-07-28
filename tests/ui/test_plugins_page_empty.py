"""Tests for the Plugin Setup page's zero-plugin branch."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QCheckBox  # noqa: E402

from joystick_diagrams.db import db_handler  # noqa: E402
from joystick_diagrams.plugins import plugin_catalog as pc  # noqa: E402
from joystick_diagrams.ui.plugins_page import PluginsPage  # noqa: E402
from joystick_diagrams.ui.widgets.plugin_empty_state import (  # noqa: E402
    PluginEmptyState,
)

SUBTITLE_WITH_PLUGINS = (
    "Enable and configure your plugins, then run them to import bindings"
)
SUBTITLE_EMPTY = "Install a plugin to import your bindings"


def _wrapper(name="DCS World", ready=True, enabled=True):
    wrapper = MagicMock()
    wrapper.name = name
    wrapper.ready = ready
    wrapper.enabled = enabled
    wrapper.error = None
    wrapper.version = "2.0.0"
    wrapper.icon = ""
    wrapper.plugin_profile_collection = None
    return wrapper


def _catalog_entry(name, plugin_type="parser", min_app_version=None):
    return pc.CatalogEntry(
        id=str(uuid4()),
        name=name,
        type=plugin_type,
        version="1.0.0",
        download_url="https://example.com/p.zip",
        sha256="0" * 64,
        min_app_version=min_app_version,
    )


@pytest.fixture(autouse=True)
def _temp_database(tmp_path):
    """Give every test a throwaway data root with a fully migrated schema.

    Constructing a real AppState builds a LabelService, which reads the
    ``bind_text`` table on init — so the schema has to exist before the page is
    built or the whole file fails on a machine (or CI runner) that has never run
    the app.

    ``db_connection`` binds ``data_root`` at import time (``from ... import
    data_root``), so patching ``joystick_diagrams.utils.data_root`` alone does not
    reach it. The binding inside ``db_connection`` is the one that decides where
    the sqlite file lives; ``db_handler.init`` uses ``utils.data_root`` via the
    module, so both are redirected to keep the developer's real database out of
    the test run.
    """
    root = tmp_path / "data_root"
    root.mkdir()
    with (
        patch("joystick_diagrams.db.db_connection.data_root", return_value=root),
        patch("joystick_diagrams.utils.data_root", return_value=root),
    ):
        db_handler.init()
        yield


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


@pytest.mark.uitest
def test_nudge_ignores_disabled_unconfigured_plugin(qapp):
    """Disabling is the natural 'not interested' action — it must silence the nudge."""
    page = _page(qapp, [_wrapper("Falcon BMS", ready=False, enabled=False)])

    page.populate_plugin_cards()

    assert page._config_nudge is None


@pytest.mark.uitest
def test_nudge_appears_immediately_when_plugin_is_enabled(qapp):
    wrapper = _wrapper("Falcon BMS", ready=False, enabled=False)
    page = _page(qapp, [wrapper])
    page.populate_plugin_cards()
    assert page._config_nudge is None

    page._on_plugin_enabled_toggled(wrapper, True)

    assert page._config_nudge is not None


@pytest.mark.uitest
def test_nudge_clears_immediately_when_plugin_is_disabled(qapp):
    wrapper = _wrapper("Falcon BMS", ready=False, enabled=True)
    page = _page(qapp, [wrapper])
    page.populate_plugin_cards()
    assert page._config_nudge is not None

    page._on_plugin_enabled_toggled(wrapper, False)

    assert page._config_nudge is None


# ── Catalog handoff to the empty-state picker ──


@pytest.mark.uitest
def test_picker_offers_only_installable_compatible_parsers(qapp):
    """The picker asks 'which games do you play?' — output plugins, incompatible
    entries, and already-installed entries must never appear in it."""
    page = _page(qapp, [])
    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()

    already_installed = _catalog_entry("Already Installed")
    page.appState.plugin_manager.loaded_plugins = [
        SimpleNamespace(id=already_installed.id, version="1.0.0")
    ]
    catalog = pc.PluginCatalog(
        plugins=[
            _catalog_entry("DCS World"),
            _catalog_entry("OpenKneeboard", plugin_type="output"),
            _catalog_entry("Future Parser", min_app_version="999.0.0"),
            already_installed,
        ]
    )

    page._on_empty_state_catalog(catalog)

    labels = {box.text() for box in page._empty_state.findChildren(QCheckBox)}
    assert labels == {"DCS World"}


@pytest.mark.uitest
def test_picker_falls_back_to_unavailable_when_nothing_is_installable(qapp):
    """An output-only catalog leaves nothing to pick, so the manual route must show."""
    from PySide6.QtWidgets import QPushButton

    page = _page(qapp, [])
    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()

    page._on_empty_state_catalog(
        pc.PluginCatalog(
            plugins=[_catalog_entry("OpenKneeboard", plugin_type="output")]
        )
    )

    assert page._empty_state.findChildren(QCheckBox) == []
    assert "Retry" in {b.text() for b in page._empty_state.findChildren(QPushButton)}


# ── Header subtitle + guidance banner ──


@pytest.mark.uitest
def test_subtitle_swaps_between_empty_and_populated(qapp):
    page = _page(qapp, [])
    with patch.object(PluginsPage, "_fetch_empty_state_catalog", autospec=True):
        page.populate_plugin_cards()

    assert page.section_header._sub_label.text() == SUBTITLE_EMPTY

    page.appState.plugin_manager.plugin_wrappers = [_wrapper()]
    page.populate_plugin_cards()

    assert page.section_header._sub_label.text() == SUBTITLE_WITH_PLUGINS


@pytest.mark.uitest
def test_guidance_banner_suppressed_when_no_plugins_installed(qapp):
    """The 'enable a plugin below' banner has nothing to point at on a fresh install."""
    page = _page(qapp, [])

    assert page._guidance_banner is None


@pytest.mark.uitest
def test_guidance_banner_shown_once_plugins_exist(qapp):
    page = _page(qapp, [_wrapper()])

    assert page._guidance_banner is not None
