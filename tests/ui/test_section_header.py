"""Tests for the SectionHeader subtitle setter."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QLabel  # noqa: E402

from joystick_diagrams.ui.widgets.section_header import SectionHeader  # noqa: E402


def _label_texts(widget) -> set[str]:
    return {label.text() for label in widget.findChildren(QLabel)}


@pytest.mark.uitest
def test_set_subtitle_replaces_existing_text(qapp):
    header = SectionHeader("fa5s.cog", "Plugin Setup", "original subtitle")

    header.set_subtitle("changed subtitle")

    texts = _label_texts(header)
    assert "changed subtitle" in texts
    assert "original subtitle" not in texts
    assert "Plugin Setup" in texts


@pytest.mark.uitest
def test_set_subtitle_creates_label_when_header_had_none(qapp):
    header = SectionHeader("fa5s.cog", "Plugin Setup")

    header.set_subtitle("added subtitle")

    assert "added subtitle" in _label_texts(header)
