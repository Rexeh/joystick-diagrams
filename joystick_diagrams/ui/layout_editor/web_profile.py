"""One app-wide ``QWebEngineProfile`` for the editor canvas and the SVG previews.

QtWebEngine requires a profile to outlive every page that uses it, otherwise it
warns "Release of profile requested but WebEnginePage still not deleted. Expect
troubles !". The profile here is created lazily (the first time a canvas or
preview is shown), is off-the-record (nothing on disk), has the ``jdeditor://``
scheme handler installed, and registers every page created on it so that
``shutdown_shared_profile()`` (connected to ``aboutToQuit``) can destroy the
pages first and the profile last. Widgets must still call their own
``shutdown()`` when they are torn down (``MainWindow._invalidate_data_pages``)
so that pages go before the profile and memory is returned early.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import shiboken6
from PySide6.QtCore import QCoreApplication
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

from joystick_diagrams.ui.layout_editor.scheme import (
    SCHEME_NAME,
    EditorSchemeHandler,
    is_scheme_registered,
)

_logger = logging.getLogger(__name__)


class ConsolePage(QWebEnginePage):
    """A page that routes JS console output to the Python logger."""

    def __init__(self, profile, on_console: Callable[[str], None] | None = None):
        super().__init__(profile)
        self._on_console = on_console

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802
        text = f"[js:{line_number}] {message}"
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            _logger.error(text)
        else:
            _logger.debug(text)
        if self._on_console is not None:
            self._on_console(text)


class _Shared:
    """Module state: the one profile, its handler and the pages created on it."""

    def __init__(self) -> None:
        self.profile: QWebEngineProfile | None = None
        self.handler: EditorSchemeHandler | None = None
        self.pages: list[QWebEnginePage] = []
        self.doc_counter = 0


_shared = _Shared()


def shared_profile() -> QWebEngineProfile:
    """The lazily created profile (with the scheme handler installed)."""
    if _shared.profile is None:
        if not is_scheme_registered():
            _logger.error(
                "jdeditor:// scheme is not registered; call register_scheme() before QApplication"
            )
        _shared.profile = QWebEngineProfile()
        _shared.handler = EditorSchemeHandler()
        _shared.profile.installUrlSchemeHandler(SCHEME_NAME, _shared.handler)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(shutdown_shared_profile)
    return _shared.profile


def shared_handler() -> EditorSchemeHandler:
    shared_profile()
    assert _shared.handler is not None
    return _shared.handler


def new_document_id(prefix: str) -> str:
    _shared.doc_counter += 1
    return f"{prefix}-{_shared.doc_counter}"


def create_page(on_console: Callable[[str], None] | None = None) -> ConsolePage:
    """A new page on the shared profile, tracked for shutdown."""
    page = ConsolePage(shared_profile(), on_console)
    _shared.pages.append(page)
    return page


def destroy_page(page: QWebEnginePage) -> None:
    """Delete ``page`` now (call after detaching it from its view and channel)."""
    if page in _shared.pages:
        _shared.pages.remove(page)
    if shiboken6.isValid(page):
        shiboken6.delete(page)


def live_page_count() -> int:
    return sum(1 for page in _shared.pages if shiboken6.isValid(page))


def shutdown_shared_profile() -> None:
    """Destroy every tracked page, then the profile and handler."""
    for page in list(_shared.pages):
        destroy_page(page)
    _shared.pages.clear()
    if _shared.profile is not None and shiboken6.isValid(_shared.profile):
        shiboken6.delete(_shared.profile)
    if _shared.handler is not None and shiboken6.isValid(_shared.handler):
        shiboken6.delete(_shared.handler)
    _shared.profile = None
    _shared.handler = None


if __name__ == "__main__":
    pass
