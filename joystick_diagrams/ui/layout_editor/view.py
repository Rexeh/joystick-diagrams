"""Widgets hosting WebEngine pages on the shared profile, with a clean teardown.

``LayoutEditorView`` hosts the editor page (``assets/editor.html``) and its
``QWebChannel`` bridge; ``show_document(svg_text, payload)`` serves the SVG over
``jdeditor://`` and tells the page to load it. ``SvgDocumentView`` shows a plain
SVG document (the Preview window). Both destroy their page before anything
else in ``shutdown()``; the profile is shared and outlives them
(``web_profile.py``).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

import shiboken6
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from joystick_diagrams.ui.layout_editor import web_profile
from joystick_diagrams.ui.layout_editor.bridge import EditorBridge
from joystick_diagrams.ui.layout_editor.scheme import EDITOR_URL, document_url

_logger = logging.getLogger(__name__)

CANVAS_BACKGROUND = "#1a1d23"
_UNIT = r'(px|mm|cm|in|pt)?"'
_WIDTH_RE = re.compile(r'\bwidth="(\d+(?:\.\d+)?)' + _UNIT)
_HEIGHT_RE = re.compile(r'\bheight="(\d+(?:\.\d+)?)' + _UNIT)
# CSS px per unit (96 dpi), so a page sized in mm fits like one sized in px
_PX_PER_UNIT = {
    "": 1.0,
    "px": 1.0,
    "mm": 96 / 25.4,
    "cm": 96 / 2.54,
    "in": 96.0,
    "pt": 96 / 72,
}


def _svg_length(pattern: re.Pattern, svg_text: str) -> float | None:
    match = pattern.search(svg_text[:4000])
    if not match:
        return None
    return float(match.group(1)) * _PX_PER_UNIT[match.group(2) or ""]


def svg_width(svg_text: str) -> float | None:
    """The root width in CSS px (units such as ``mm`` converted at 96 dpi)."""
    return _svg_length(_WIDTH_RE, svg_text)


def svg_height(svg_text: str) -> float | None:
    return _svg_length(_HEIGHT_RE, svg_text)


class _WebHost(QWidget):
    """Shared page/view lifetime handling."""

    consoleMessage = Signal(str)

    def __init__(self, doc_prefix: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._shut_down = False
        self._doc_id = web_profile.new_document_id(doc_prefix)
        self._rev = 0
        self._page = web_profile.create_page(self.consoleMessage.emit)
        self._page.setBackgroundColor(QColor(CANVAS_BACKGROUND))
        self._view = QWebEngineView(self)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._view.setPage(self._page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    @property
    def revision(self) -> int:
        return self._rev

    @property
    def is_shut_down(self) -> bool:
        return self._shut_down

    def web_view(self) -> QWebEngineView | None:
        return None if self._shut_down else self._view

    def _serve(self, svg_text: str) -> str:
        self._rev += 1
        web_profile.shared_handler().set_document(
            self._doc_id, svg_text.encode("utf-8")
        )
        return document_url(self._doc_id, self._rev)

    def run_js(self, script: str, callback: Callable | None = None) -> None:
        if self._shut_down:
            return
        if callback is None:
            self._page.runJavaScript(script)
        else:
            self._page.runJavaScript(script, 0, callback)

    def shutdown(self) -> None:
        """Destroy page then view, synchronously; the shared profile stays."""
        if self._shut_down:
            return
        self._shut_down = True
        page, view = self._page, self._view
        self._page = self._view = None  # type: ignore[assignment]
        self._before_page_destroyed(page)
        view.setPage(None)
        web_profile.destroy_page(page)
        view.setParent(None)
        if shiboken6.isValid(view):
            shiboken6.delete(view)
        try:
            web_profile.shared_handler().remove_document(self._doc_id)
        except RuntimeError:  # profile already gone at app exit
            pass

    def _before_page_destroyed(self, page) -> None:
        pass

    def closeEvent(self, event):  # noqa: N802
        self.shutdown()
        super().closeEvent(event)


class LayoutEditorView(_WebHost):
    """The editor canvas. ``show_document`` pushes a rendered SVG and its state."""

    pageReady = Signal(str)

    def __init__(
        self, parent: QWidget | None = None, bridge: EditorBridge | None = None
    ):
        super().__init__("editor", parent)
        self._loaded = False
        self._booted = False
        self._pending: tuple[str, dict[str, Any]] | None = None
        self.bridge = bridge or EditorBridge(parent=self)
        self.bridge.page_ready.connect(self._on_page_ready)
        self._channel = QWebChannel(self._page)
        self._channel.registerObject("bridge", self.bridge)
        self._page.setWebChannel(self._channel)

    def show_document(self, svg_text: str, payload: dict[str, Any]) -> None:
        """Serve ``svg_text`` and tell the page to load it with ``payload`` (state)."""
        url = self._serve(svg_text)
        if not self._booted:
            self._pending = (url, payload)
            if not self._loaded:
                self._loaded = True
                self._view.load(QUrl(EDITOR_URL))
            return
        self.bridge.push_document(url, payload)

    def _on_page_ready(self, timings_json: str) -> None:
        if not self._booted:
            self._booted = True
            if self._pending is not None:
                url, payload = self._pending
                self._pending = None
                self.bridge.push_document(url, payload)
                return
        self.pageReady.emit(timings_json)

    def _before_page_destroyed(self, page) -> None:
        page.setWebChannel(None)


class SvgDocumentView(_WebHost):
    """A read-only SVG viewer (Preview window): ``show_svg`` then ``set_zoom``."""

    loadFinished = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("preview", parent)
        self._last_svg: str | None = None
        self._view.loadFinished.connect(self.loadFinished.emit)

    @property
    def last_svg(self) -> str | None:
        return self._last_svg

    def show_svg(self, svg_text: str) -> None:
        self._last_svg = svg_text
        self._view.load(QUrl(self._serve(svg_text)))

    def set_zoom(self, factor: float) -> None:
        if not self._shut_down:
            self._view.setZoomFactor(max(0.1, min(5.0, factor)))

    def zoom(self) -> float:
        return 1.0 if self._shut_down else self._view.zoomFactor()

    def fit_width(self) -> float | None:
        """Zoom so the SVG's width fills the view; returns the factor used."""
        if self._shut_down or not self._last_svg:
            return None
        width = svg_width(self._last_svg)
        if not width:
            return None
        factor = max(0.1, min(5.0, (self._view.width() - 24) / width))
        self.set_zoom(factor)
        return factor

    def fit_page(self) -> float | None:
        """Zoom so the whole SVG (width and height) fits the view."""
        if self._shut_down or not self._last_svg:
            return None
        width, height = svg_width(self._last_svg), svg_height(self._last_svg)
        if not width or not height:
            return self.fit_width()
        factor = min(
            (self._view.width() - 24) / width, (self._view.height() - 24) / height
        )
        factor = max(0.1, min(5.0, factor))
        self.set_zoom(factor)
        return factor


if __name__ == "__main__":
    pass
