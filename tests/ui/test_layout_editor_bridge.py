"""The QWebChannel bridge: gesture validation and the signals it re-emits.

Qt objects only; no QWebEngine and no display beyond the offscreen platform.
"""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.ui.layout_editor.bridge import (  # noqa: E402
    EditorBridge,
    GestureError,
    parse_gesture,
)


def test_parse_move_requires_numeric_deltas():
    gesture = parse_gesture(
        {"gesture": "move", "target": "button_1#1", "dx": 12, "dy": -3.5}
    )
    assert gesture == {
        "gesture": "move",
        "target": "button_1#1",
        "dx": 12.0,
        "dy": -3.5,
    }
    with pytest.raises(GestureError):
        parse_gesture({"gesture": "move", "target": "button_1", "dx": "12", "dy": 0})
    with pytest.raises(GestureError):
        parse_gesture({"gesture": "move", "target": "button_1", "dx": 1})
    with pytest.raises(GestureError):
        parse_gesture({"gesture": "move", "target": "", "dx": 1, "dy": 1})


def test_parse_resize_needs_positive_size_and_rejects_unknown_kinds():
    gesture = parse_gesture(
        {
            "gesture": "resize",
            "target": "button_1",
            "dx": 0,
            "dy": -2,
            "width": 140,
            "height": 30,
        }
    )
    assert gesture["width"] == 140.0 and gesture["dy"] == -2.0
    with pytest.raises(GestureError):
        parse_gesture(
            {
                "gesture": "resize",
                "target": "b",
                "dx": 0,
                "dy": 0,
                "width": 0,
                "height": 10,
            }
        )
    with pytest.raises(GestureError):
        parse_gesture({"gesture": "teleport", "target": "button_1"})


@pytest.mark.uitest
def test_bridge_emits_validated_gestures_and_rejections(qapp):
    bridge = EditorBridge()
    accepted, rejected = [], []
    bridge.gesture.connect(accepted.append)
    bridge.gesture_rejected.connect(rejected.append)

    reply = json.loads(
        bridge.applyGesture(
            json.dumps({"gesture": "move", "target": "button_2#1", "dx": 3, "dy": 4})
        )
    )
    assert reply == {"ok": True}
    assert accepted == [
        {"gesture": "move", "target": "button_2#1", "dx": 3.0, "dy": 4.0}
    ]

    reply = json.loads(bridge.applyGesture("not json"))
    assert reply["ok"] is False
    assert rejected and "Expecting value" in rejected[0]


@pytest.mark.uitest
def test_bridge_relays_selection_nudges_history_and_zoom(qapp):
    bridge = EditorBridge()
    seen: dict[str, list] = {
        "sel": [],
        "nudge": [],
        "undo": [],
        "redo": [],
        "hide": [],
        "note": [],
        "zoom": [],
    }
    bridge.selection_changed.connect(seen["sel"].append)
    bridge.nudged.connect(lambda t, x, y: seen["nudge"].append((t, x, y)))
    bridge.undo_requested.connect(lambda: seen["undo"].append(1))
    bridge.redo_requested.connect(lambda: seen["redo"].append(1))
    bridge.hide_requested.connect(seen["hide"].append)
    bridge.note_edit_requested.connect(seen["note"].append)
    bridge.zoom_changed.connect(seen["zoom"].append)

    bridge.selectSlot("button_1#1")
    bridge.selectSlot("")
    bridge.nudge("button_1#1", 1, 0)
    bridge.nudge("button_1#1", 0, 0)  # no-op
    bridge.undo()
    bridge.redo()
    bridge.hideSelected("button_3#1")
    bridge.editNote("0123456789abcdef0123456789abcdef")
    bridge.zoomChanged(150)

    assert seen["sel"] == ["button_1#1", ""]
    assert bridge.selected is None
    assert seen["nudge"] == [("button_1#1", 1, 0)]
    assert seen["undo"] == [1] and seen["redo"] == [1]
    assert seen["hide"] == ["button_3#1"]
    assert seen["note"] == ["0123456789abcdef0123456789abcdef"]
    assert seen["zoom"] == [150] and bridge.zoom_percent == 150


@pytest.mark.uitest
def test_bridge_pushes_documents_and_requests_to_the_page(qapp):
    bridge = EditorBridge()
    pushed, selects, zooms = [], [], []
    bridge.documentChanged.connect(lambda url, payload: pushed.append((url, payload)))
    bridge.selectRequested.connect(selects.append)
    bridge.zoomRequested.connect(zooms.append)

    bridge.push_document("jdeditor://app/doc/editor-1.svg?rev=1", {"slots": []})
    bridge.request_select("button_9#1")
    bridge.request_zoom("fit")

    assert pushed == [("jdeditor://app/doc/editor-1.svg?rev=1", '{"slots":[]}')]
    assert selects == ["button_9#1"] and bridge.selected == "button_9#1"
    assert zooms == ["fit"]
