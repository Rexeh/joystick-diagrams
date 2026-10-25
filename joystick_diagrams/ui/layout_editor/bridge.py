"""QWebChannel bridge between the JS canvas and the Layout page (plan §5.2).

The page JS only reports *gestures* and *intent*; Python owns the op model,
persistence and undo. The bridge validates what comes in and re-emits it as Qt
signals the page controller (``ui/customise_layout.py``) listens to.

Called from JS (slots)::

    ready(timings_json)                  the document finished loading
    applyGesture(json)                   {"gesture":"move","target":k,"dx":..,"dy":..}
                                         {"gesture":"resize","target":k,"dx":..,"dy":..,
                                          "width":..,"height":..}  (dx/dy: top-left shift)
    selectSlot(target)                   "" clears the selection
    nudge(target, dx, dy)                arrow keys (1 px, Shift: 10 px)
    undo() / redo()                      Ctrl+Z / Ctrl+Y
    hideSelected(target)                 Delete key
    editNote(uid)                        double-click on a note
    zoomChanged(percent)
    log(message) / report(json)

Sent to JS (signals)::

    documentChanged(url, payload_json)   load a new SVG; payload = EditorRender.as_dict()
                                         plus "selected", "profileLabel"
    selectRequested(target)              select from the Qt side
    zoomRequested(command)               "in" | "out" | "fit" | "100"
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

_logger = logging.getLogger(__name__)

GESTURES = frozenset({"move", "resize"})
_NUMERIC = {
    "move": ("dx", "dy"),
    "resize": ("dx", "dy", "width", "height"),
}


class GestureError(ValueError):
    """Raised when a gesture from the page fails validation."""


def _number(raw: Mapping[str, Any], name: str) -> float:
    value = raw.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GestureError(f"{name} must be a number, got {value!r}")
    return float(value)


def parse_gesture(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a raw gesture dict from the page."""
    kind = raw.get("gesture")
    if kind not in GESTURES:
        raise GestureError(f"unknown gesture {kind!r}")
    target = str(raw.get("target") or "").strip()
    if not target:
        raise GestureError(f"{kind} requires a target")
    gesture: dict[str, Any] = {"gesture": kind, "target": target}
    for name in _NUMERIC[kind]:
        gesture[name] = _number(raw, name)
    if kind == "resize" and (gesture["width"] <= 0 or gesture["height"] <= 0):
        raise GestureError("resize needs a positive width and height")
    return gesture


class EditorBridge(QObject):
    """The object JS sees as ``bridge`` through QWebChannel.

    Slots are camelCase because they are called from JS (``ui/`` ignores N rules).
    """

    # → JS
    documentChanged = Signal(str, str)
    selectRequested = Signal(str)
    zoomRequested = Signal(str)
    # → Python
    page_ready = Signal(str)
    gesture = Signal(dict)
    gesture_rejected = Signal(str)
    selection_changed = Signal(str)
    nudged = Signal(str, int, int)
    undo_requested = Signal()
    redo_requested = Signal()
    hide_requested = Signal(str)
    note_edit_requested = Signal(str)
    zoom_changed = Signal(int)
    reported = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected: str | None = None
        self.zoom_percent: int = 100
        self.ready_count = 0

    # ── Called from JS ──

    @Slot(str)
    def ready(self, timings_json: str) -> None:
        self.ready_count += 1
        self.page_ready.emit(timings_json)

    @Slot(str, result=str)
    def applyGesture(self, gesture_json: str) -> str:
        try:
            parsed = parse_gesture(json.loads(gesture_json))
        except (ValueError, TypeError) as exc:  # json errors subclass ValueError
            _logger.warning("Rejected layout gesture %s: %s", gesture_json[:200], exc)
            self.gesture_rejected.emit(str(exc))
            return json.dumps({"ok": False, "error": str(exc)})
        self.gesture.emit(parsed)
        return json.dumps({"ok": True})

    @Slot(str)
    def selectSlot(self, target: str) -> None:
        self.selected = target or None
        self.selection_changed.emit(target or "")

    @Slot(str, int, int)
    def nudge(self, target: str, dx: int, dy: int) -> None:
        if target and (dx or dy):
            self.nudged.emit(target, int(dx), int(dy))

    @Slot()
    def undo(self) -> None:
        self.undo_requested.emit()

    @Slot()
    def redo(self) -> None:
        self.redo_requested.emit()

    @Slot(str)
    def hideSelected(self, target: str) -> None:
        if target:
            self.hide_requested.emit(target)

    @Slot(str)
    def editNote(self, uid: str) -> None:
        if uid:
            self.note_edit_requested.emit(uid)

    @Slot(int)
    def zoomChanged(self, percent: int) -> None:
        self.zoom_percent = int(percent)
        self.zoom_changed.emit(int(percent))

    @Slot(str)
    def report(self, report_json: str) -> None:
        self.reported.emit(report_json)

    @Slot(str)
    def log(self, message: str) -> None:
        _logger.info("editor.js: %s", message)

    # ── Called from Python ──

    def push_document(self, url: str, payload: Mapping[str, Any]) -> None:
        self.documentChanged.emit(url, json.dumps(payload, separators=(",", ":")))

    def request_select(self, target: str | None) -> None:
        self.selected = target or None
        self.selectRequested.emit(target or "")

    def request_zoom(self, command: str) -> None:
        self.zoomRequested.emit(command)


if __name__ == "__main__":
    pass
