"""Route Qt's own messages into the app log, demoting known harmless noise.

Thumbnails are drawn off the UI thread (``template_catalog.render_thumbnail``,
``ui/pages_dialog.render_thumbnail``). QtSvg and QPainter print warnings for
things that don't affect the picture: "QPainter::begin: Paint device returned
engine == 0" when a worker paints into a zero-sized or released image while the
dialog closes, and "Could not parse node: font" for the draw.io font tags in
almost every template. Those go to the debug log; every other Qt message keeps
its level under the ``qt`` logger, so nothing real is lost.

``install_qt_message_filter()`` is idempotent and safe to call before the
``QApplication`` exists. The handler runs on whichever thread Qt logs from;
``logging`` is thread-safe.
"""

from __future__ import annotations

import logging
import re

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

_logger = logging.getLogger("qt")

NOISE = (
    re.compile(
        r"QPainter::\w+: (Paint device returned engine == 0|Painter not active)"
    ),
    re.compile(r"QPainter::end: Painter not active"),
    re.compile(r"Could not parse node: font"),
    re.compile(r"QFont::setPointSizeF: Point size <= 0"),
)

_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}

_installed = False


def is_noise(message: str) -> bool:
    return any(pattern.search(message) for pattern in NOISE)


def level_for(msg_type: QtMsgType, message: str) -> int:
    if is_noise(message):
        return logging.DEBUG
    return _LEVELS.get(msg_type, logging.WARNING)


def _handler(msg_type: QtMsgType, context, message: str) -> None:  # noqa: ARG001
    category = getattr(context, "category", None)
    text = f"{category}: {message}" if category and category != "default" else message
    _logger.log(level_for(msg_type, message), text)


def install_qt_message_filter() -> None:
    global _installed  # noqa: PLW0603 - one handler per process
    if _installed:
        return
    qInstallMessageHandler(_handler)
    _installed = True


__all__ = ["install_qt_message_filter", "is_noise", "level_for"]
