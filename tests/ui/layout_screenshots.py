"""Offscreen screenshot driver for the Layout screen and its dialogs.

Not a test module. Runs the real widgets with the app's qt-material stylesheet
and QtWebEngine on the offscreen platform (software GL), seeds a throwaway
database with one device/two profiles on the Starter Template, and writes PNGs::

    uv run python tests/ui/layout_screenshots.py OUT_DIR

Outputs: 01_layout_page.png (selected slot, added box, note, hidden slot,
profile-only outline, +N badge, notices), 02_auto_add.png, 03_save_as.png,
04_preview.png.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from joystick_diagrams.ui.layout_editor.scheme import register_scheme  # noqa: E402

register_scheme()
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

from qt_material import apply_stylesheet  # noqa: E402

apply_stylesheet(
    app,
    theme="dark_blue.xml",
    invert_secondary=False,
    extra={"font_family": "Roboto"},
    css_file=str(REPO_ROOT / "theme" / "custom.css"),
)


def pump(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def wait_until(predicate, timeout_ms: int = 15000, step: int = 50) -> bool:
    waited = 0
    while waited < timeout_ms:
        if predicate():
            return True
        pump(step)
        waited += step
    return False


def grab(widget: QWidget, path: Path) -> None:
    pump(300)
    widget.grab().save(str(path))
    print("wrote", path)


def main(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    data_root = Path(tempfile.mkdtemp(prefix="jd-shots-"))
    patches = [
        patch("joystick_diagrams.db.db_connection.data_root", return_value=data_root),
        patch("joystick_diagrams.utils.data_root", return_value=data_root),
    ]
    for item in patches:
        item.start()
    from joystick_diagrams.db import db_handler

    db_handler.init()

    from joystick_diagrams.render.layout import (
        TEMPLATE_LAYER,
        AddNoteOp,
        HideOp,
        MoveOp,
    )
    from joystick_diagrams.ui import strings_layout as S
    from joystick_diagrams.ui.diagrams_page import DiagramsPage
    from joystick_diagrams.ui.layout_auto_add_dialog import AutoAddDialog
    from joystick_diagrams.ui.layout_editor import web_profile
    from joystick_diagrams.ui.layout_editor.planning import SceneCache
    from joystick_diagrams.ui.layout_save_template_dialog import SaveTemplateDialog
    from joystick_diagrams.ui.preview_window import PreviewWindow
    from tests.ui.layout_fixtures import DEVICE_GUID, seed_layout_state

    state = seed_layout_state()
    service = state.layout_service
    key = "bundled:Starter Template.svg"
    # Stored changes: template layer (saved against other bytes so the
    # "template was updated" notice shows), plus a profile-only move.
    service.set_ops(
        key,
        TEMPLATE_LAYER,
        [
            MoveOp(target="button_21", dx=0, dy=-12),
            HideOp(target="button_30"),
            AddNoteOp(
                text="PROFILE_NAME · CURRENT_DATE", x=600, y=640, width=240, height=26
            ),
            MoveOp(target="button_99", dx=5, dy=5),  # no such slot any more
        ],
        "an-older-hash",
    )
    service.set_ops(
        key, "dcs world_f-16c", [MoveOp(target="button_11", dx=18, dy=0)], None
    )

    page = DiagramsPage()
    page.resize(1500, 920)
    page.show()
    page.show_layout(DEVICE_GUID)
    layout = page.layout_screen
    assert wait_until(lambda: layout._render is not None), "render never finished"
    assert wait_until(
        lambda: layout._canvas is not None and layout._canvas.bridge.ready_count >= 2
    ), "canvas never ready"
    layout._select("button_1#1")
    layout.add_modifier_box()  # planner-placed, becomes the selection
    assert wait_until(
        lambda: (
            layout._selected not in (None, "button_1#1")
            and not layout._render_timer.isActive()
        )
    ), "box was not added"
    pump(400)
    layout._select("button_1#1")
    pump(600)
    grab(page, out_dir / "01_layout_page.png")

    entry = layout.current_diagram()
    export_device = layout._export_device
    auto = AutoAddDialog(
        scene=SceneCache().scene_for(entry.template),
        render=layout._render,
        export_device=export_device,
        all_devices=[ed.device for ed in entry.export_devices],
        scope_text=S.SCOPE_ALL_PROFILES,
        parent=page,
    )
    auto.which_any.setChecked(True)
    auto.show()
    grab(auto, out_dir / "02_auto_add.png")
    auto.close()

    save = SaveTemplateDialog(
        template=entry.template,
        session=layout._session,
        export_device=export_device,
        device_name=entry.device_name,
        device_id=entry.device_id,
        theme=state.theme_service.resolved_active(),
        parent=page,
    )
    save.show()
    grab(save, out_dir / "03_save_as.png")
    save.close()

    preview = PreviewWindow(entry.export_devices, export_device, page)
    preview.show()
    assert wait_until(lambda: preview.last_outcome is not None), (
        "preview never rendered"
    )
    pump(800)
    grab(preview, out_dir / "04_preview.png")
    preview.close()

    page.shutdown()
    page.close()
    web_profile.shutdown_shared_profile()
    for item in patches:
        item.stop()
    return 0


if __name__ == "__main__":
    out = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else REPO_ROOT / "build" / "layout-screenshots"
    )
    code = main(out)
    app.processEvents()
    sys.exit(code)
