"""Render review samples of manual layout ops on three template variants.

Not a test module (no ``test_`` prefix). On a cell-id template (WinWing Orion2
18 Joystick Combo), a flat one (VKB Gladiator NXT R) and a grouped one (Virpil
Constellation ALPHA R) the script moves a slot that has a leader line, resizes
another, hides one, adds four modifier boxes to ``BUTTON_1`` and adds a note,
then renders the result through the real pipeline and checks that the exported
draw.io model reflects every op (geometry, visibility, new cells).

Usage::

    QT_QPA_PLATFORM=offscreen QT_OPENGL=software \\
    QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --no-sandbox" \\
    uv run python -m tests.render.make_layout_samples OUT_DIR [--png]
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from joystick_diagrams.export import render_template
from joystick_diagrams.input.button import Button
from joystick_diagrams.modifier_identity import ModifierRegistrySnapshot
from joystick_diagrams.render import RenderContext
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.editor import EditorOptions, render_for_editor
from joystick_diagrams.render.layout import (
    AddModifierBoxesOp,
    AddNoteOp,
    HideOp,
    LayoutDocument,
    MoveOp,
    ResizeOp,
)
from joystick_diagrams.template import Template
from tests.render.make_layout_contact_sheet import contact_device, convert_to_png
from tests.render.render_fixtures import REPO_ROOT, export_device_for

NOW = datetime(2026, 10, 20, 12, 0, 0)
SAMPLES = (
    REPO_ROOT
    / "templates"
    / "WinWing"
    / "Orion2 18 Joystick Combo"
    / "Orion2 18 Joystick Combo.svg",
    REPO_ROOT / "templates" / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg",
    REPO_ROOT / "templates" / "Virpil" / "Virpil Constellation ALPHA R.svg",
)
SVG = "{http://www.w3.org/2000/svg}"


def choose_ops(template: Template) -> tuple[list, dict[str, str]]:
    """Pick targets from the template's own structure; return ops and what they are."""
    preview = render_for_editor(template, None, options=EditorOptions(annotate=False))
    actions = [
        s for s in preview.slots if s.role == "action" and s.movable and not s.added_uid
    ]
    with_edge = [s for s in actions if s.edges]
    move = (with_edge or actions)[0]
    resize = next(
        (s for s in actions if s.resizable and s.target != move.target), actions[-1]
    )
    hide = next(
        (s for s in with_edge if s.target not in (move.target, resize.target)),
        next(s for s in actions if s.target not in (move.target, resize.target)),
    )
    ops = [
        MoveOp(target=move.target, dx=40, dy=-25),
        ResizeOp(
            target=resize.target,
            width=resize.bbox.width * 1.3,
            height=resize.bbox.height * 1.4,
        ),
        HideOp(target=hide.target),
        AddModifierBoxesOp(target="button_1", count=4, max_count=4, arrangement="auto"),
        AddNoteOp(
            text="PROFILE_NAME exported CURRENT_DATE", x=20, y=20, width=220, height=26
        ),
    ]
    return ops, {"move": move.target, "resize": resize.target, "hide": hide.target}


def verify(svg_text: str, ops: list, before: dict[str, dict]) -> list[str]:
    """Check the exported model reflects the ops; return human-readable findings."""
    root = etree.fromstring(svg_text.encode("utf-8"), make_parser())
    model = DrawioModel.from_content(root.get("content"))
    cells = model.cells_by_id()
    findings: list[str] = []
    for op in ops:
        if isinstance(op, MoveOp):
            cell = cells[before["move"]["cell"]]
            geo = cell.geometry
            ok = (
                abs(geo.x - before["move"]["x"] - op.dx) < 0.01
                and abs(geo.y - before["move"]["y"] - op.dy) < 0.01
            )
            findings.append(
                f"move {op.target}: model geometry {'moved' if ok else 'NOT moved'} ({geo.x}, {geo.y})"
            )
        elif isinstance(op, ResizeOp):
            geo = cells[before["resize"]["cell"]].geometry
            ok = abs(geo.width - op.width) < 0.01 and abs(geo.height - op.height) < 0.01
            findings.append(
                f"resize {op.target}: model size {'ok' if ok else 'WRONG'} ({geo.width}x{geo.height})"
            )
        elif isinstance(op, HideOp):
            cell = cells[before["hide"]["cell"]]
            findings.append(
                f"hide {op.target}: model visible={cell.visible} (expect False)"
            )
        elif isinstance(op, AddModifierBoxesOp):
            added = [
                c
                for c in cells.values()
                if (c.id or "").startswith("jd-")
                and "MODIFIER" in c.label.upper()
                or (c.id or "").startswith("jd-")
                and c.style_dict.get("jdAdded")
                and "jdNote" not in c.style_dict
            ]
            findings.append(
                f"add boxes: {len(added)} jd- modifier cells in model, labels {[c.plain_label[:18] for c in added][:4]}"
            )
        elif isinstance(op, AddNoteOp):
            notes = [c for c in cells.values() if c.style_dict.get("jdNote")]
            findings.append(
                f"note: {len(notes)} note cell(s), label {notes[0].plain_label if notes else None!r}"
            )
    wrappers = [g for g in root.iter(f"{SVG}g") if g.get("data-jd-op")]
    findings.append(f"rendered wrappers: {[g.get('data-jd-op') for g in wrappers]}")
    return findings


def render_samples(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        for path in SAMPLES:
            template = Template(str(path))
            ops, targets = choose_ops(template)
            preview = render_for_editor(
                template, None, options=EditorOptions(annotate=False)
            )
            # Remember the model geometry of the targets before the ops.
            raw_model = DrawioModel.from_content(
                etree.fromstring(template.raw_data.encode("utf-8"), make_parser()).get(
                    "content"
                )
            )
            before: dict[str, dict] = {}
            for kind, target in targets.items():
                slot = next(s for s in preview.slots if s.target == target)
                cell = _cell_for_slot(template, raw_model, slot)
                before[kind] = {
                    "cell": cell.id,
                    "x": cell.geometry.x,
                    "y": cell.geometry.y,
                }
            device = contact_device(template)
            device.create_input(Button(1), "Trigger")
            for n, key in enumerate(("LShift", "LCtrl", "LAlt", "RShift"), start=1):
                device.add_modifier_to_input(Button(1), {key}, f"Trigger alt {n}")
            key = template.template_key
            ctx = RenderContext(
                colour_modifiers=True,
                registry=ModifierRegistrySnapshot.default(colouring_enabled=True),
                layouts={(key, "", ""): LayoutDocument(template_key=key, ops=ops)},
                engine_override="dom",
                now=NOW,
            )
            export_device = export_device_for(
                template.raw_data, device, "Sample profile"
            )
            export_device.template = template
            outcome = render_template(export_device, ctx)
            target = out_dir / f"{path.stem} - manual ops.svg"
            target.write_text(outcome.svg_text, encoding="utf-8")
            written.append(target)
            print(
                f"== {path.name}: adapter={outcome.report.adapter} notices={[n.value for n in outcome.report.notices]} targets={targets}"
            )
            for line in verify(outcome.svg_text, ops, before):
                print("   ", line)
    return written


def _cell_for_slot(template: Template, model: DrawioModel, slot):
    """The pristine model cell behind an editor slot (same label, same position)."""
    from joystick_diagrams.render.adapters import detect_adapter
    from joystick_diagrams.render.document import TemplateDocument
    from joystick_diagrams.render.layout_scene import build_scene

    doc = TemplateDocument.parse(template.raw_data)
    fresh_model = DrawioModel.from_content(doc.root.get("content"))
    slot_map = detect_adapter(doc, fresh_model).build_slots(doc, fresh_model)
    scene = build_scene(slot_map, doc.root, fresh_model)
    group = scene.group(slot.target)
    return model.cells_by_id()[group.cells[0].id]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args(argv)
    written = render_samples(args.out_dir)
    if args.png:
        convert_to_png(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
