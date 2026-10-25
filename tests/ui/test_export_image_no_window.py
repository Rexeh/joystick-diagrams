"""PNG/PDF conversion never shows a window.

On Wayland the old ``view.move(-10000, -10000); view.show()`` trick put a window
titled "__main__.py" on screen for every export batch (clients can't position
themselves there). ``PngConverter`` now prints PDFs from a view-less
``QWebEnginePage`` and grabs PNGs from one view made with ``WA_DontShowOnScreen``,
so no native top-level window is ever created.
"""

import os
import shutil
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

import pytest  # noqa: E402

pytest.importorskip("PySide6.QtWebEngineWidgets")

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from joystick_diagrams import export_image  # noqa: E402
from joystick_diagrams.export_image import WINDOW_TITLE, PngConverter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (
    REPO_ROOT / "templates" / "Thrustmaster" / "Thrustmaster Warthog - Throttle.svg"
)


def _visible_windows() -> list[str]:
    return [
        f"{type(w).__name__}:{w.title()!r}"
        for w in QGuiApplication.topLevelWindows()
        if w.isVisible()
    ]


@pytest.mark.uitest
def test_converter_creates_no_visible_top_level_window(qapp, qtbot, tmp_path):
    before = set(_visible_windows())
    jobs = []
    for name in ("one", "two"):
        source = tmp_path / f"{name}.png.svg"
        shutil.copy(TEMPLATE, source)
        jobs.append((str(source), str(tmp_path / f"{name}.png")))
    pdf_source = tmp_path / "page.pdf.svg"
    shutil.copy(TEMPLATE, pdf_source)
    jobs.append((str(pdf_source), str(tmp_path / "page.pdf")))

    views = []
    real_make_view = export_image.make_render_view

    def recording_make_view(parent=None):
        view = real_make_view(parent)
        views.append(
            (
                view.testAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen),
                view.windowTitle(),
                bool(view.windowFlags() & Qt.WindowType.Tool),
            )
        )
        return view

    seen: list[str] = []
    poll = QTimer()
    poll.timeout.connect(
        lambda: seen.extend(w for w in _visible_windows() if w not in before)
    )
    poll.start(10)
    converter = PngConverter(jobs)
    with (
        patch.object(export_image, "make_render_view", recording_make_view),
        qtbot.waitSignal(converter.finished, timeout=120000),
    ):
        converter.start()
    poll.stop()
    QApplication.processEvents()

    assert seen == [], seen
    # One off-screen view for the whole batch (the PDF needs no view at all)
    assert views == [(True, WINDOW_TITLE, True)]
    for name in ("one", "two"):
        image = QImage(str(tmp_path / f"{name}.png"))
        assert not image.isNull() and image.width() > 100
    assert (tmp_path / "page.pdf").stat().st_size > 1000
    assert not any(tmp_path.glob("*.svg"))  # inputs are cleaned up
