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


# CSS absolute units → px at 96 dpi (what Chromium uses for an SVG viewport)
_PX_PER_UNIT = {
    "px": 1.0,
    "": 1.0,
    "mm": 96.0 / 25.4,
    "cm": 96.0 / 2.54,
    "in": 96.0,
    "pt": 96.0 / 72.0,
    "pc": 16.0,
}
_DIMENSION_RE = r'{name}="\s*(\d+(?:\.\d+)?)\s*(px|mm|cm|in|pt|pc)?'


def _dimension_px(header: str, name: str, default: int) -> int:
    match = re.search(_DIMENSION_RE.format(name=name), header)
    if not match:
        return default
    unit = (match.group(2) or "").lower()
    if unit in ("", "px"):
        return int(float(match.group(1)))  # unchanged px behaviour
    return max(int(round(float(match.group(1)) * _PX_PER_UNIT[unit])), 1)


def parse_svg_dimensions(svg_path: Path) -> tuple[int, int]:
    """Extract width and height (CSS px) from an SVG file's root element.

    Plain numbers and ``px`` are read as before; ``mm``/``cm``/``in``/``pt``/``pc``
    (combined pages are sized in mm) are converted at 96 dpi.
    """
    with open(svg_path, "r", encoding="utf-8") as f:
        header = f.read(2000)

    return _dimension_px(header, "width", 800), _dimension_px(header, "height", 600)


def parse_svg_page_size_mm(svg_path: Path) -> tuple[float, float] | None:
    """(width, height) in mm when the root declares a physical size, else ``None``."""
    with open(svg_path, "r", encoding="utf-8") as f:
        header = f.read(2000)
    sizes = []
    for name in ("width", "height"):
        match = re.search(_DIMENSION_RE.format(name=name), header)
        unit = (match.group(2) or "").lower() if match else ""
        if not match or unit in ("", "px"):
            return None
        sizes.append(float(match.group(1)) * _PX_PER_UNIT[unit] * 25.4 / 96.0)
    return sizes[0], sizes[1]


WINDOW_TITLE = "Joystick Diagrams"


def make_render_view(parent=None):
    """A ``QWebEngineView`` that renders and can be grabbed but never appears.

    ``move(-10000, -10000)`` + ``show()`` keeps a window off screen on X11 and
    Windows, but Wayland ignores client positions, so the view popped up as a
    window titled after the script. ``WA_DontShowOnScreen`` makes Qt treat the
    widget as shown (Chromium renders, ``grab()`` works) without mapping a
    native window; the title and Tool flag are belt and braces.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWebEngineWidgets import QWebEngineView

    view = QWebEngineView(parent)
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    view.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    if parent is None:
        view.setWindowFlags(view.windowFlags() | Qt.WindowType.Tool)
    view.setWindowTitle(WINDOW_TITLE)
    view.show()
    return view


def _looks_blank(pixmap) -> bool:
    """True for a null grab or one that is a single flat colour (nothing painted)."""
    if pixmap.isNull():
        return True
    image = pixmap.toImage()
    width, height = image.width(), image.height()
    if width == 0 or height == 0:
        return True
    first = image.pixel(0, 0)
    steps = 12
    for i in range(1, steps):
        for j in range(1, steps):
            if image.pixel(width * i // steps, height * j // steps) != first:
                return False
    return True


def _hidden_child_host():
    """Fallback parent for platforms where ``WA_DontShowOnScreen`` grabs blank:
    the main window's central widget (the view is stacked underneath its
    siblings, so it renders inside the app's own window instead of a new one)."""
    try:
        from joystick_diagrams.app_state import AppState

        window = AppState().main_window
    except Exception:  # noqa: BLE001 - no app state (scripts, tests)
        window = None
    return window.centralWidget() if window is not None else None


class PngConverter(QObject):
    """Converts a queue of SVG files to PNG (or PDF) with QtWebEngine.

    Must be used on the main thread. Processes files one at a time using a
    local event loop so the main event loop stays responsive between files.

    No window is ever shown (Wayland ignores off-screen positions):

    - a target ending in ``.pdf`` is loaded into a view-less ``QWebEnginePage``
      and printed with ``printToPdf`` at the SVG's physical size (combined pages
      are sized in mm), no margins;
    - a ``.png`` target is grabbed from one ``QWebEngineView`` made with
      ``WA_DontShowOnScreen`` (``make_render_view``); if that grab is blank on
      some platform, the view moves inside the main window, stacked underneath.

    One page and one view per batch, torn down (page before view) at the end.
    """

    progress = Signal(int, int)  # current, total
    finished = Signal()

    def __init__(self, conversions: list[tuple[str, str]], scale: int = 2):
        super().__init__()
        self._queue = [(Path(s), Path(p)) for s, p in conversions]
        self._total = len(self._queue)
        self._current = 0
        self._scale = scale
        self._view = None
        self._pdf_page = None
        self._fallback_used = False

    def start(self):
        # Process the first file after a brief delay to let the UI update
        QTimer.singleShot(100, self._process_queue)

    def _process_queue(self):
        """Process all files sequentially, yielding to the event loop between each."""
        for svg_path, out_path in self._queue:
            self._current += 1
            try:
                if out_path.suffix.lower() == ".pdf":
                    self._convert_pdf(svg_path, out_path)
                else:
                    self._convert_png(svg_path, out_path)
            except Exception as e:  # noqa: BLE001 - one file never stops the batch
                _logger.error(f"Conversion failed for {svg_path}: {e}")

            # Clean up intermediate SVG
            try:
                svg_path.unlink(missing_ok=True)
            except OSError:
                pass

            self.progress.emit(self._current, self._total)
            # Let UI repaint between files
            QApplication.processEvents()

        self._teardown()
        self.finished.emit()

    def _teardown(self) -> None:
        if self._pdf_page is not None:
            self._pdf_page.deleteLater()
            self._pdf_page = None
        if self._view is not None:
            page = self._view.page()
            self._view.setParent(None)
            self._view.close()
            if page is not None:
                page.deleteLater()
            self._view.deleteLater()
            self._view = None

    # ── Loading ──

    @staticmethod
    def _load(target, svg_path: Path) -> bool:
        """Load ``svg_path`` into a view or page and wait for it (with a timeout)."""
        loop = QEventLoop()
        loaded_ok = [False]

        def on_load(ok):
            loaded_ok[0] = ok
            loop.quit()

        target.loadFinished.connect(on_load)
        target.load(QUrl.fromLocalFile(str(svg_path.resolve())))
        QTimer.singleShot(_LOAD_TIMEOUT_MS, loop.quit)
        loop.exec()
        target.loadFinished.disconnect(on_load)
        if not loaded_ok[0]:
            _logger.error(f"Failed to load SVG (timeout or error): {svg_path}")
        return loaded_ok[0]

    @staticmethod
    def _settle(ms: int = _RENDER_DELAY_MS) -> None:
        paint_loop = QEventLoop()
        QTimer.singleShot(ms, paint_loop.quit)
        paint_loop.exec()

    # ── PNG ──

    def _ensure_view(self):
        if self._view is None:
            self._view = make_render_view()
        return self._view

    def _convert_png(self, svg_path: Path, png_path: Path) -> None:
        """Load a single SVG in the view, wait for render, grab to PNG."""
        view = self._ensure_view()
        width, height = parse_svg_dimensions(svg_path)
        # Native SVG size; zoomFactor for crisp higher-resolution output.
        view.setFixedSize(QSize(width * self._scale, height * self._scale))
        view.setZoomFactor(self._scale)
        if not self._load(view, svg_path):
            return
        self._settle()
        pixmap = view.grab()
        if _looks_blank(pixmap) and not self._fallback_used:
            pixmap = self._grab_inside_main_window(view) or pixmap
        if pixmap.isNull():
            _logger.error(f"grab() returned null pixmap for {svg_path}")
            return
        pixmap.save(str(png_path), "PNG")
        _logger.info(f"Exported PNG ({pixmap.width()}x{pixmap.height()}) to {png_path}")

    def _grab_inside_main_window(self, view):
        """Re-host the view as a child of the main window, underneath its siblings."""
        host = _hidden_child_host()
        if host is None:
            return None
        from PySide6.QtCore import Qt

        _logger.info("Blank grab off screen; rendering inside the main window instead")
        self._fallback_used = True
        view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        view.setParent(host)
        view.move(0, 0)
        view.lower()
        view.show()
        self._settle()
        return view.grab()

    # ── PDF ──

    def _ensure_pdf_page(self):
        if self._pdf_page is None:
            from PySide6.QtWebEngineCore import QWebEnginePage

            self._pdf_page = QWebEnginePage(self)
        return self._pdf_page

    def _convert_pdf(self, svg_path: Path, pdf_path: Path) -> None:
        """Print the SVG to PDF at its physical size (A4 when unknown); no view."""
        from PySide6.QtCore import QMarginsF, QSizeF
        from PySide6.QtGui import QPageLayout, QPageSize

        page = self._ensure_pdf_page()
        if not self._load(page, svg_path):
            return
        self._settle(100)

        size_mm = parse_svg_page_size_mm(svg_path)
        page_size = (
            QPageSize(
                QSizeF(*size_mm),
                QPageSize.Unit.Millimeter,
                "",
                QPageSize.SizeMatchPolicy.ExactMatch,
            )
            if size_mm
            else QPageSize(QPageSize.PageSizeId.A4)
        )
        layout = QPageLayout(
            page_size, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)
        )

        loop = QEventLoop()
        done = [False]

        def on_printed(path, ok):
            done[0] = ok
            loop.quit()

        page.pdfPrintingFinished.connect(on_printed)
        page.printToPdf(str(pdf_path), layout)
        QTimer.singleShot(_LOAD_TIMEOUT_MS, loop.quit)
        loop.exec()
        page.pdfPrintingFinished.disconnect(on_printed)

        if done[0]:
            _logger.info(f"Exported PDF to {pdf_path}")
        else:
            _logger.error(f"PDF printing failed or timed out for {svg_path}")
