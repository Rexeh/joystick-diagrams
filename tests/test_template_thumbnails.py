"""Thumbnails: QSvgRenderer → PNG cache, footer removed, Starter gets the icon.

Needs a QGuiApplication; pytest-qt's ``qapp`` provides one on the offscreen
platform. Skipped when QtSvg is not importable.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtSvg")

from joystick_diagrams import template_catalog as catalog  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def data_root(tmp_path):
    root = tmp_path / "data_root"
    root.mkdir()
    with patch("joystick_diagrams.utils.data_root", return_value=root):
        yield root


def _vkb() -> catalog.TemplateInfo:
    return next(i for i in catalog.bundled_templates() if "Gladiator NXT R" in i.name)


def test_thumbnail_is_rendered_once_and_cached(qapp, data_root):
    from PySide6.QtGui import QImage

    info = _vkb()
    path = catalog.thumbnail_for(info)
    assert path == data_root / "cache" / "thumbs" / f"{info.content_hash}.png"
    assert path.is_file()
    image = QImage(str(path))
    assert image.width() == 320
    # aspect preserved: 1159 × 807 → 320 × 223
    assert image.height() == round(320 * 807 / 1159)
    with patch("joystick_diagrams.template_catalog.render_thumbnail") as render:
        assert catalog.thumbnail_for(info) == path
        render.assert_not_called()


def test_other_widths_get_their_own_file(qapp, data_root):
    info = _vkb()
    path = catalog.thumbnail_for(info, size=(160, None))
    assert path.name == f"{info.content_hash}-w160.png"
    from PySide6.QtGui import QImage

    assert QImage(str(path)).width() == 160


def test_footer_and_model_are_removed_before_rendering(qapp):
    info = _vkb()
    prepared = catalog.thumbnail_svg_bytes(info)
    assert b"Text is not SVG" not in prepared
    assert b" content=" not in prepared
    assert b"<svg" in prepared


def test_starter_template_gets_the_generic_icon(qapp, data_root):
    from PySide6.QtGui import QImage

    with patch("joystick_diagrams.template_catalog.thumbnail_svg_bytes") as svg_bytes:
        path = catalog.thumbnail_for(catalog.starter_template())
        svg_bytes.assert_not_called()
    image = QImage(str(path))
    assert (image.width(), image.height()) == (320, 240)


def test_unreadable_svg_falls_back_to_the_icon(qapp, tmp_path):
    bad = tmp_path / "bad.svg"
    bad.write_text("<svg xmlns='http://www.w3.org/2000/svg'><g></svg>")
    info = catalog.info_for_path(bad)
    path = catalog.thumbnail_for(info)
    assert path.is_file()


def test_requires_a_gui_application(qapp):
    with (
        patch("PySide6.QtGui.QGuiApplication.instance", return_value=None),
        pytest.raises(catalog.ThumbnailUnavailableError),
    ):
        catalog.render_thumbnail(_vkb(), Path(os.devnull), (320, None))
