"""Smoke tests for the Plugin Store dialog's row/badge/action rendering.

Exercises the pure widget-building logic without network or a full AppState by
building an uninitialised dialog instance (the tested methods don't touch __init__
state beyond bound methods).
"""

import os
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.plugins import plugin_catalog as pc  # noqa: E402
from joystick_diagrams.ui.plugin_store_dialog import PluginStoreDialog  # noqa: E402


def _item(status, *, signed=True, compatible=True, version="1.0.0", installed=None):
    entry = pc.CatalogEntry(
        id=str(uuid4()),
        name="Sample",
        type="parser",
        version=version,
        signed=signed,
        download_url="https://example.com/p.zip",
        sha256="0" * 64,
        min_app_version="9.9.9" if not compatible else None,
    )
    return pc.CatalogItemStatus(
        entry=entry, status=status, installed_version=installed, compatible=compatible
    )


@pytest.fixture
def dialog(qapp):
    # Build without running __init__ (avoids AppState/network); methods under test
    # only rely on the class, not instance state.
    return PluginStoreDialog.__new__(PluginStoreDialog)


@pytest.mark.uitest
def test_action_button_available_is_install(dialog):
    btn = dialog._action_button(_item(pc.CatalogStatus.AVAILABLE))
    assert btn.text() == "Install"
    assert btn.isEnabled()


@pytest.mark.uitest
def test_action_button_installed_is_disabled(dialog):
    btn = dialog._action_button(_item(pc.CatalogStatus.INSTALLED))
    assert btn.text() == "Installed"
    assert not btn.isEnabled()


@pytest.mark.uitest
def test_action_button_update_shows_target_version(dialog):
    btn = dialog._action_button(
        _item(pc.CatalogStatus.UPDATE_AVAILABLE, version="2.5.0", installed="2.0.0")
    )
    assert "2.5.0" in btn.text()
    assert btn.isEnabled()


@pytest.mark.uitest
def test_action_button_incompatible_is_disabled(dialog):
    btn = dialog._action_button(_item(pc.CatalogStatus.AVAILABLE, compatible=False))
    assert not btn.isEnabled()
    assert "9.9.9" in btn.text()


@pytest.mark.uitest
def test_trust_badges(dialog):
    assert PluginStoreDialog._trust_badge(True).text() == "Verified"
    assert PluginStoreDialog._trust_badge(False).text() == "Community"
