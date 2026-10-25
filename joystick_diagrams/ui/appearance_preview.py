"""Live diagram preview for the Appearance screen.

Renders one ``ExportDevice`` through the real pipeline (``export.render_template``)
off the UI thread, debounced, and shows the SVG in a lazily created
``QWebEngineView``. The view is only created once the widget is shown, so tests
and headless runs never start WebEngine. Small SVGs are served with
``setContent`` (``image/svg+xml``); anything near the 2 MB ``setContent`` limit
goes through a temp file instead (the largest bundled template is 2.69 MB).

``refresh()`` is cheap by design: nothing renders unless ``mark_dirty()`` was
called since the last render and the widget is visible.
"""

import logging
import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QRunnable,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from joystick_diagrams.render import RenderContext, RenderOutcome
from joystick_diagrams.ui import strings_appearance as S

_logger = logging.getLogger(__name__)

SET_CONTENT_LIMIT_BYTES = 1_800_000
DEBOUNCE_MS = 300
_DIMENSION_RE = re.compile(r'\b(width|height)="(\d+(?:\.\d+)?)(?:px)?"')


def svg_width(svg_text: str) -> float | None:
    match = re.search(r'\bwidth="(\d+(?:\.\d+)?)(?:px)?"', svg_text[:4000])
    return float(match.group(1)) if match else None


class _RenderSignals(QObject):
    done = Signal(int, object)  # generation, RenderOutcome
    failed = Signal(int, str)


class _RenderRunnable(QRunnable):
    def __init__(self, generation: int, export_device, ctx: RenderContext):
        super().__init__()
        self.generation = generation
        self.export_device = export_device
        self.ctx = ctx
        self.signals = _RenderSignals()

    @Slot()
    def run(self) -> None:
        from joystick_diagrams.export import render_template

        try:
            outcome = render_template(self.export_device, self.ctx)
        except (
            Exception
        ) as e:  # pragma: no cover - defensive; render_template falls back itself
            _logger.error(f"Preview render failed: {e}", exc_info=True)
            self.signals.failed.emit(self.generation, str(e))
            return
        self.signals.done.emit(self.generation, outcome)


class AppearancePreview(QWidget):
    """``set_source(export_device, context_factory)`` then ``mark_dirty()`` to render."""

    render_finished = Signal(object)  # RenderOutcome
    render_started = Signal()

    def __init__(self, parent: QWidget | None = None, debounce_ms: int = DEBOUNCE_MS):
        super().__init__(parent)
        self._export_device = None
        self._context_factory: Callable[[], RenderContext] | None = None
        self._dirty = False
        self._generation = 0
        self._view = None
        self._temp_file: Path | None = None
        self._last_svg: str | None = None
        self._pool = QThreadPool.globalInstance()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._start_render)

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel(S.PREVIEW_RENDERING)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(
            "color: #9AA0A6; font-style: italic; background: #252830; "
            "border: 1px solid #3C4043; border-radius: 6px;"
        )
        self._stack.addWidget(self._placeholder)
        self.setMinimumHeight(240)

    # ── API ──

    def set_source(
        self, export_device, context_factory: Callable[[], RenderContext]
    ) -> None:
        self._export_device = export_device
        self._context_factory = context_factory
        self.mark_dirty()

    def mark_dirty(self) -> None:
        """Schedule a debounced re-render (only runs while visible)."""
        self._dirty = True
        if self.isVisible():
            self._timer.start()

    def refresh(self) -> None:
        """Cheap: re-render only when something changed since the last render."""
        if self._dirty and self.isVisible():
            self._timer.start()

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def last_svg(self) -> str | None:
        return self._last_svg

    def web_view(self):
        return self._view

    # ── Rendering ──

    def _start_render(self) -> None:
        if self._export_device is None or self._context_factory is None:
            self._placeholder.setText(S.PREVIEW_EMPTY)
            self._stack.setCurrentWidget(self._placeholder)
            self._dirty = False
            return
        self._dirty = False
        self._generation += 1
        if self._stack.currentWidget() is self._placeholder:
            self._placeholder.setText(S.PREVIEW_RENDERING)
        self.render_started.emit()
        runnable = _RenderRunnable(
            self._generation, self._export_device, self._context_factory()
        )
        runnable.signals.done.connect(self._on_rendered)
        runnable.signals.failed.connect(self._on_failed)
        self._pool.start(runnable)

    def _on_rendered(self, generation: int, outcome: RenderOutcome) -> None:
        if generation != self._generation:
            return  # a newer render is on its way
        self._last_svg = outcome.svg_text
        self._show_svg(outcome.svg_text)
        self.render_finished.emit(outcome)

    def _on_failed(self, generation: int, message: str) -> None:
        if generation != self._generation:
            return
        _logger.warning(f"Appearance preview failed: {message}")
        self._placeholder.setText(S.PREVIEW_FAILED)
        self._stack.setCurrentWidget(self._placeholder)

    def _ensure_view(self):
        if self._view is not None:
            return self._view
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError as e:  # pragma: no cover - WebEngine is a hard dependency
            _logger.error(f"QtWebEngine unavailable for the preview: {e}")
            return None
        self._view = QWebEngineView(self)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._view.loadFinished.connect(lambda _ok: self._fit_zoom())
        self._stack.addWidget(self._view)
        return self._view

    def _show_svg(self, svg_text: str) -> None:
        view = self._ensure_view()
        if view is None:
            return
        data = svg_text.encode("utf-8")
        if len(data) <= SET_CONTENT_LIMIT_BYTES:
            view.setContent(data, "image/svg+xml")
        else:
            self._write_temp(data)
            view.load(QUrl.fromLocalFile(str(self._temp_file)))
        self._stack.setCurrentWidget(view)

    def _write_temp(self, data: bytes) -> None:
        if self._temp_file is None:
            handle = tempfile.NamedTemporaryFile(
                prefix="jd-preview-", suffix=".svg", delete=False
            )
            handle.close()
            self._temp_file = Path(handle.name)
        self._temp_file.write_bytes(data)

    def _fit_zoom(self) -> None:
        if self._view is None or not self._last_svg:
            return
        width = svg_width(self._last_svg)
        if not width:
            return
        available = max(self._view.width() - 8, 50)
        self._view.setZoomFactor(max(0.2, min(2.0, available / width)))

    # ── Qt events ──

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if self._dirty:
            self._timer.start()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._fit_zoom()

    def shutdown(self) -> None:
        self._timer.stop()
        self._generation += 1  # drop in-flight results
        if self._view is not None:
            self._stack.removeWidget(self._view)
            self._view.setParent(None)
            self._view.deleteLater()
            self._view = None
        if self._temp_file is not None:
            try:
                self._temp_file.unlink(missing_ok=True)
            except OSError:
                pass
            self._temp_file = None

    def closeEvent(self, event):  # noqa: N802
        self.shutdown()
        super().closeEvent(event)
