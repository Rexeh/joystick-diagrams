"""``jdeditor://`` URL scheme for the layout editor and the SVG previews.

The scheme must be registered **before** ``QApplication`` is constructed
(``app_init`` does this next to ``AA_ShareOpenGLContexts``). The handler serves
the editor page, its JS/CSS and any number of in-memory SVG documents
(``jdeditor://app/doc/<id>.svg?rev=N``), so there are no temp files and no
``setHtml``/``setContent`` 2 MB ceiling (the largest bundled template is 2.69 MB).

Everything lives under one host (``jdeditor://app/...``) so that ``fetch()`` from
the editor page is same-origin and needs no CORS headers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QBuffer, QFile, QIODevice
from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestJob,
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
)

_logger = logging.getLogger(__name__)

SCHEME_NAME = b"jdeditor"
HOST = "app"
BASE_URL = f"{SCHEME_NAME.decode()}://{HOST}"
EDITOR_URL = f"{BASE_URL}/editor.html"
DOC_PREFIX = "/doc/"
WEBCHANNEL_JS_PATH = "/qwebchannel.js"
ASSETS_DIR = Path(__file__).parent / "assets"

_MIME_TYPES = {
    ".html": b"text/html; charset=utf-8",
    ".js": b"application/javascript; charset=utf-8",
    ".css": b"text/css; charset=utf-8",
    ".svg": b"image/svg+xml; charset=utf-8",
    ".png": b"image/png",
}


def is_scheme_registered() -> bool:
    return bytes(QWebEngineUrlScheme.schemeByName(SCHEME_NAME).name()) == SCHEME_NAME


def register_scheme() -> bool:
    """Register ``jdeditor://``. Returns False when it was already registered.

    Qt refuses (with a warning) to register schemes after the application object
    exists, so call this from the entry point before ``QApplication(...)``.
    """
    if is_scheme_registered():
        return False

    scheme = QWebEngineUrlScheme(SCHEME_NAME)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    flags = (
        QWebEngineUrlScheme.Flag.SecureScheme
        | QWebEngineUrlScheme.Flag.LocalAccessAllowed
        | QWebEngineUrlScheme.Flag.CorsEnabled
    )
    # Qt >= 6.6: needed for fetch()/XHR to a custom scheme.
    fetch_flag = getattr(QWebEngineUrlScheme.Flag, "FetchApiAllowed", None)
    if fetch_flag is not None:
        flags |= fetch_flag
    scheme.setFlags(flags)
    QWebEngineUrlScheme.registerScheme(scheme)
    return True


def document_path(doc_id: str) -> str:
    return f"{DOC_PREFIX}{doc_id}.svg"


def document_url(doc_id: str, rev: int) -> str:
    return f"{BASE_URL}{document_path(doc_id)}?rev={rev}"


class EditorSchemeHandler(QWebEngineUrlSchemeHandler):
    """Serves editor assets and in-memory SVG documents over ``jdeditor://app/``."""

    def __init__(self, parent=None, assets_dir: Path = ASSETS_DIR):
        super().__init__(parent)
        self._assets_dir = assets_dir.resolve()
        self._documents: dict[str, bytes] = {}
        self.requests_served = 0

    # ── Documents ──

    def set_document(self, doc_id: str, data: bytes) -> None:
        self._documents[doc_id] = bytes(data)

    def remove_document(self, doc_id: str) -> None:
        self._documents.pop(doc_id, None)

    def document_size(self, doc_id: str) -> int:
        return len(self._documents.get(doc_id, b""))

    # ── Qt ──

    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:  # noqa: N802
        path = job.requestUrl().path()
        payload = self._payload_for(path)
        if payload is None:
            _logger.warning("jdeditor: not found: %s", path)
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        data, mime = payload
        # The buffer is parented to the job so it lives exactly as long as the reply.
        buffer = QBuffer(job)
        buffer.setData(data)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.requests_served += 1
        job.reply(mime, buffer)

    def _payload_for(self, path: str) -> tuple[bytes, bytes] | None:
        if path.startswith(DOC_PREFIX) and path.endswith(".svg"):
            doc_id = path[len(DOC_PREFIX) : -4]
            data = self._documents.get(doc_id)
            return (data, _MIME_TYPES[".svg"]) if data is not None else None
        if path == WEBCHANNEL_JS_PATH:
            return self._read_qrc(":/qtwebchannel/qwebchannel.js"), _MIME_TYPES[".js"]

        candidate = (self._assets_dir / path.lstrip("/")).resolve()
        if not candidate.is_file() or self._assets_dir not in candidate.parents:
            return None
        mime = _MIME_TYPES.get(candidate.suffix.lower(), b"application/octet-stream")
        return candidate.read_bytes(), mime

    @staticmethod
    def _read_qrc(resource: str) -> bytes:
        qfile = QFile(resource)
        if not qfile.open(QIODevice.OpenModeFlag.ReadOnly):
            return b""
        try:
            return bytes(qfile.readAll().data())
        finally:
            qfile.close()


if __name__ == "__main__":
    pass
