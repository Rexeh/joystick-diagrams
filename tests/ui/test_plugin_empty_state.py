"""Tests for the zero-plugin empty state widget."""

import os
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QCheckBox, QPushButton  # noqa: E402

from joystick_diagrams.plugins import plugin_catalog as pc  # noqa: E402
from joystick_diagrams.ui.widgets.plugin_empty_state import (  # noqa: E402
    PluginEmptyState,
)

BROWSE_TEXT = "Browse plugin store"
ZIP_TEXT = "Install from ZIP..."


def _entry(name="DCS World"):
    return pc.CatalogEntry(
        id=str(uuid4()),
        name=name,
        type="parser",
        version="2.0.0",
        description=f"Parse {name} keybinds.",
        download_url="https://example.com/p.zip",
        sha256="0" * 64,
    )


def _button_texts(widget) -> set[str]:
    return {b.text() for b in widget.findChildren(QPushButton)}


def _checkboxes(widget) -> list[QCheckBox]:
    return widget.findChildren(QCheckBox)


@pytest.mark.uitest
def test_catalog_renders_one_checkbox_per_entry(qapp):
    widget = PluginEmptyState()

    widget.set_catalog([_entry("DCS World"), _entry("Star Citizen")])

    labels = {box.text() for box in _checkboxes(widget)}
    assert labels == {"DCS World", "Star Citizen"}


@pytest.mark.uitest
def test_empty_catalog_shows_message_and_retry_not_checkboxes(qapp):
    widget = PluginEmptyState()

    widget.set_catalog([])

    assert _checkboxes(widget) == []
    assert "Retry" in _button_texts(widget)


@pytest.mark.uitest
def test_unavailable_offers_retry(qapp):
    widget = PluginEmptyState()

    widget.set_unavailable()

    assert "Retry" in _button_texts(widget)


@pytest.mark.uitest
def test_action_row_present_in_every_state(qapp):
    """The manual install route must never disappear — this is the offline guarantee."""
    widget = PluginEmptyState()

    for apply_state in (
        widget.set_loading,
        lambda: widget.set_catalog([_entry()]),
        lambda: widget.set_catalog([]),
        widget.set_unavailable,
    ):
        apply_state()
        texts = _button_texts(widget)
        assert BROWSE_TEXT in texts
        assert ZIP_TEXT in texts


@pytest.mark.uitest
def test_install_requested_carries_only_checked_entries(qapp):
    widget = PluginEmptyState()
    dcs, star = _entry("DCS World"), _entry("Star Citizen")
    widget.set_catalog([dcs, star])
    received = []
    widget.install_requested.connect(received.append)

    boxes = {box.text(): box for box in _checkboxes(widget)}
    boxes["Star Citizen"].setChecked(True)
    widget._emit_install()

    assert received == [[star]]


@pytest.mark.uitest
def test_install_button_disabled_until_something_selected(qapp):
    widget = PluginEmptyState()
    widget.set_catalog([_entry()])

    assert widget._install_button.isEnabled() is False

    _checkboxes(widget)[0].setChecked(True)

    assert widget._install_button.isEnabled() is True
    assert widget._install_button.text() == "Install 1 plugin"


@pytest.mark.uitest
def test_drop_zone_forwards_dropped_path(qapp, tmp_path):
    widget = PluginEmptyState()
    received = []
    widget.zip_dropped.connect(received.append)

    widget.drop_zone.file_dropped.emit(tmp_path / "plugin.zip")

    assert received == [tmp_path / "plugin.zip"]
