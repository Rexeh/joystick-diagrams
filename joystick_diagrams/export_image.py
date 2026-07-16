"""SVG to PNG conversion using QWebEngineView for accurate rendering.

draw.io SVG templates use <foreignObject> for HTML text rendering, which
QSvgRenderer cannot handle. QWebEngineView (Chromium-based) renders these
perfectly but must run on the main thread — so conversion is done as a
post-processing step after SVG files are saved by the export worker thread.
"""

import logging
import re
from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, QSize, QTimer, QUrl, Signal
from PySide6.QtWidgets import QApplication

_logger = logging.getLogger(__name__)

# Timeout per file in case WebEngine hangs (ms)
_LOAD_TIMEOUT_MS = 15000
# Delay after load to allow rendering to complete before grab (ms)
_RENDER_DELAY_MS = 500


def parse_svg_dimensions(svg_path: Path) -> tuple[int, int]:
    """Extract width and height from an SVG file's root element."""
    with open(svg_path, "r", encoding="utf-8") as f:
        header = f.read(2000)

    width_match = re.search(r'width="(\d+)', header)
    height_match = re.search(r'height="(\d+)', header)

    width = int(width_match.group(1)) if width_match else 800
    height = int(height_match.group(1)) if height_match else 600

    return width, height


class PngConverter(QObject):
    """Converts a queue of SVG files to PNG using QWebEngineView.

    Must be used on the main thread. Processes files one at a time using
    a local event loop so the main event loop stays responsive between files.
    """

    progress = Signal(int, int)  # current, total
    finished = Signal()

    def __init__(self, conversions: list[tuple[str, str]], scale: int = 2):
        super().__init__()
        self._queue = [(Path(s), Path(p)) for s, p in conversions]
        self._total = len(self._queue)
        self._current = 0
        self._scale = scale

    def start(self):
        # Process the first file after a brief delay to let the UI update
        QTimer.singleShot(100, self._process_queue)

    def _process_queue(self):
        """Process all files sequentially, yielding to the event loop between each."""
        from PySide6.QtWebEngineWidgets import QWebEngineView

        view = QWebEngineView()
        # Position offscreen but show it — WebEngine needs a visible widget to render
        view.move(-10000, -10000)
        view.show()

        for svg_path, png_path in self._queue:
            self._current += 1

            try:
                self._convert_one(view, svg_path, png_path)
            except Exception as e:
                _logger.error(f"PNG conversion failed for {svg_path}: {e}")

            # Clean up intermediate SVG
            try:
                svg_path.unlink(missing_ok=True)
            except OSError:
                pass

            self.progress.emit(self._current, self._total)
            # Let UI repaint between files
            QApplication.processEvents()

        view.close()
        view.deleteLater()
        self.finished.emit()

    def _convert_one(self, view, svg_path: Path, png_path: Path):
        """Load a single SVG in the view, wait for render, grab to PNG."""
        width, height = parse_svg_dimensions(svg_path)

        # Set view to native SVG size — the SVG fills the viewport exactly.
        # Use zoomFactor for crisp higher-resolution output.
        view.setFixedSize(QSize(width * self._scale, height * self._scale))
        view.setZoomFactor(self._scale)

        loop = QEventLoop()
        loaded_ok = [False]

        def on_load(ok):
            loaded_ok[0] = ok
            loop.quit()

        view.loadFinished.connect(on_load)

        # Load the SVG
        view.load(QUrl.fromLocalFile(str(svg_path.resolve())))

        # Wait for loadFinished with a timeout
        QTimer.singleShot(_LOAD_TIMEOUT_MS, loop.quit)
        loop.exec()

        view.loadFinished.disconnect(on_load)

        if not loaded_ok[0]:
            _logger.error(f"Failed to load SVG (timeout or error): {svg_path}")
            return

        # Give the renderer time to paint after loading
        paint_loop = QEventLoop()
        QTimer.singleShot(_RENDER_DELAY_MS, paint_loop.quit)
        paint_loop.exec()

        pixmap = view.grab()

        if not pixmap.isNull():
            pixmap.save(str(png_path), "PNG")
            _logger.info(
                f"Exported PNG ({pixmap.width()}x{pixmap.height()}) to {png_path}"
            )
        else:
            _logger.error(f"grab() returned null pixmap for {svg_path}")
