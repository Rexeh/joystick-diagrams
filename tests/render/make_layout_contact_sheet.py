"""Spike S6 contact sheet: auto-add modifier boxes over every bundled template.

Not a test module (no ``test_`` prefix). For each ``templates/**/*.svg`` a
synthetic device binds every discovered input with a command and **three**
modifiers; ``auto_layout.plan_auto_add`` plans up to three boxes per input and
the result is rendered through the real pipeline (boxes filled and coloured by
key). Per template the script reports inputs/boxes requested, placed and
unplaced, and an independent overlap count of the placed boxes against the
template's occupied rectangles.

Exit criteria (plan §9.1 S6): zero overlaps, and at least 80 % of inputs placed
on at least 35 of the 46 templates.

Usage::

    QT_QPA_PLATFORM=offscreen QT_OPENGL=software \\
    QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --no-sandbox" \\
    uv run python -m tests.render.make_layout_contact_sheet OUT_DIR [--png] [--arrangement auto]

Writes ``<template>.svg`` (and ``.png`` with ``--png``), ``summary.md``,
``summary.json`` and, with ``--png``, a ``contact_sheet.png`` montage.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from joystick_diagrams.export import render_template
from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.modifier_identity import ModifierRegistrySnapshot
from joystick_diagrams.render import RenderContext
from joystick_diagrams.render.adapters import detect_adapter
from joystick_diagrams.render.auto_layout import (
    AutoAddResult,
    PlanOptions,
    counts_from_device,
    plan_auto_add,
)
from joystick_diagrams.render.document import TemplateDocument
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.layout import LayoutDocument
from joystick_diagrams.render.layout_scene import LayoutScene, build_scene
from joystick_diagrams.template import Template
from tests.render.render_fixtures import REPO_ROOT, export_device_for, new_device

NOW = datetime(2026, 10, 20, 12, 0, 0)
MODIFIER_KEYS = ("LShift", "LCtrl", "LAlt")
MODIFIERS_PER_INPUT = 3
PASS_RATIO = 0.8
PASS_TEMPLATES = 35


@dataclass
class TemplateStats:
    name: str
    adapter: str
    inputs: int
    inputs_full: int  # every requested box placed
    inputs_partial: int  # at least one box placed
    boxes_requested: int
    boxes_placed: int
    boxes_unplaced: int
    overlaps: int
    notices: list[str]

    @property
    def input_ratio(self) -> float:
        return self.inputs_full / self.inputs if self.inputs else 1.0

    @property
    def passes(self) -> bool:
        return self.overlaps == 0 and self.input_ratio >= PASS_RATIO


# ── Synthetic device ──


def _control_for(token: str):
    parts = token.upper().split("_")
    if parts[0] == "BUTTON" and len(parts) == 2 and parts[1].isdigit():
        return Button(int(parts[1]))
    if parts[0] == "AXIS":
        if len(parts) == 3 and parts[1] == "SLIDER" and parts[2].isdigit():
            return AxisSlider(int(parts[2]))
        if len(parts) == 2 and parts[1] in AxisDirection.__members__:
            return Axis(AxisDirection[parts[1]])
    if parts[0] == "POV" and len(parts) == 3 and parts[2] in HatDirection.__members__:
        return Hat(int(parts[1]), HatDirection[parts[2]])
    return None


def contact_device(template: Template) -> Device_:
    """Every discovered input bound, each with ``MODIFIERS_PER_INPUT`` modifiers."""
    device = new_device("Contact sheet device")
    tokens = sorted(
        template.get_template_buttons()
        | template.get_template_axis()
        | template.get_template_hats()
    )
    for token in tokens:
        control = _control_for(token)
        if control is None:
            continue
        device.create_input(control, f"Action {token.upper()}")
        for n, key in enumerate(MODIFIER_KEYS[:MODIFIERS_PER_INPUT], start=1):
            device.add_modifier_to_input(control, {key}, f"Alt {n}")
    return device


# ── Planning and rendering ──


def plan_template(
    template: Template, device: Device_, arrangement: str
) -> tuple[AutoAddResult, LayoutScene, dict[str, int]]:
    doc = TemplateDocument.parse(template.raw_data)
    model = DrawioModel.from_content(doc.root.get("content"))
    slot_map = detect_adapter(doc, model).build_slots(doc, model)
    scene = build_scene(slot_map, doc.root, model)
    counts = {
        key: count
        for key, count in counts_from_device(device, MODIFIERS_PER_INPUT).items()
        if scene.primary_for_input(key) is not None
    }
    options = PlanOptions(arrangement=arrangement, max_count=MODIFIERS_PER_INPUT)
    result = plan_auto_add(scene, counts, options)
    return result, scene, counts


def stats_for(
    name: str,
    adapter: str,
    result: AutoAddResult,
    scene: LayoutScene,
    counts: dict[str, int],
) -> TemplateStats:
    placed_per_input: dict[str, int] = {}
    for box in result.placed:
        placed_per_input[box.target] = placed_per_input.get(box.target, 0) + 1
    requested = sum(counts.values())
    full = sum(
        1
        for key, wanted in counts.items()
        if placed_per_input.get(f"{key}#1", 0) >= wanted
    )
    partial = sum(1 for key in counts if placed_per_input.get(f"{key}#1", 0) > 0)
    return TemplateStats(
        name=name,
        adapter=adapter,
        inputs=len(counts),
        inputs_full=full,
        inputs_partial=partial,
        boxes_requested=requested,
        boxes_placed=len(result.placed),
        boxes_unplaced=requested - len(result.placed),
        overlaps=result.overlaps(scene.occupied()),
        notices=sorted({u.reason for u in result.unplaced}),
    )


def render_with_ops(template: Template, device: Device_, result: AutoAddResult) -> str:
    key = template.template_key
    layouts = {(key, ""): LayoutDocument(template_key=key, ops=list(result.ops))}
    ctx = RenderContext(
        colour_modifiers=True,
        registry=ModifierRegistrySnapshot.default(colouring_enabled=True),
        layouts=layouts,
        engine_override="dom",
        now=NOW,
    )
    export_device = export_device_for(template.raw_data, device, "Contact sheet")
    export_device.template = template
    outcome = render_template(export_device, ctx)
    return outcome.svg_text


def run(out_dir: Path, arrangement: str, png: bool) -> list[TemplateStats]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[TemplateStats] = []
    written: list[Path] = []
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        for path in sorted((REPO_ROOT / "templates").rglob("*.svg")):
            template = Template(str(path))
            device = contact_device(template)
            result, scene, counts = plan_template(template, device, arrangement)
            adapter = detect_adapter(
                TemplateDocument.parse(template.raw_data),
                DrawioModel.from_content(
                    TemplateDocument.parse(template.raw_data).root.get("content")
                ),
            ).name
            row = stats_for(path.stem, adapter, result, scene, counts)
            rows.append(row)
            target = out_dir / f"{path.stem}.svg"
            target.write_text(
                render_with_ops(template, device, result), encoding="utf-8"
            )
            written.append(target)
            print(
                f"{row.name[:48]:48} inputs={row.inputs:3} full={row.inputs_full:3} boxes={row.boxes_placed:3}/{row.boxes_requested:3} overlaps={row.overlaps} {'PASS' if row.passes else 'FAIL'}"
            )
    write_summary(out_dir, rows, arrangement)
    if png:
        convert_to_png(written)
        make_montage(
            [p.with_suffix(".png") for p in written], out_dir / "contact_sheet.png"
        )
    return rows


def write_summary(out_dir: Path, rows: list[TemplateStats], arrangement: str) -> None:
    passing = sum(1 for r in rows if r.passes)
    overlaps = sum(r.overlaps for r in rows)
    lines = [
        f"# S6 auto-add contact sheet (arrangement={arrangement})",
        "",
        f"Templates passing (0 overlaps and >= {PASS_RATIO:.0%} of inputs fully placed): "
        f"**{passing}/{len(rows)}** (criterion: >= {PASS_TEMPLATES}). Total overlaps: **{overlaps}**.",
        "",
        "| Template | Adapter | Inputs | Fully placed | Partially | Boxes placed | Unplaced | Overlaps | Result |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.name} | {r.adapter} | {r.inputs} | {r.inputs_full} ({r.input_ratio:.0%}) | "
            f"{r.inputs_partial} | {r.boxes_placed}/{r.boxes_requested} | {r.boxes_unplaced} | "
            f"{r.overlaps} | {'PASS' if r.passes else 'FAIL'} |"
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "summary.json").write_text(
        json.dumps([asdict(r) for r in rows], indent=2), encoding="utf-8"
    )
    print("\n".join(lines[:3]))


# ── PNG output (offscreen QtWebEngine) ──


def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    return QApplication.instance() or QApplication(sys.argv)


def convert_to_png(svg_paths: list[Path], scale: int = 1) -> None:
    app = _qt_app()
    from joystick_diagrams.export_image import PngConverter

    jobs: list[tuple[str, str]] = []
    for svg in svg_paths:
        scratch = svg.with_suffix(".png.svg")  # PngConverter deletes its input
        shutil.copyfile(svg, scratch)
        jobs.append((str(scratch), str(svg.with_suffix(".png"))))
    converter = PngConverter(jobs, scale=scale)
    converter.finished.connect(app.quit)
    converter.start()
    app.exec()


def make_montage(
    png_paths: list[Path], target: Path, columns: int = 6, cell: int = 320
) -> None:
    _qt_app()
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage, QPainter

    existing = [p for p in png_paths if p.exists()]
    rows = (len(existing) + columns - 1) // columns
    sheet = QImage(
        columns * cell, max(rows, 1) * (cell + 18), QImage.Format.Format_RGB32
    )
    sheet.fill(QColor("white"))
    painter = QPainter(sheet)
    for index, path in enumerate(existing):
        image = QImage(str(path)).scaled(
            cell - 8,
            cell - 8,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (index % columns) * cell + 4
        y = (index // columns) * (cell + 18) + 4
        painter.drawImage(x, y, image)
        painter.setPen(QColor("black"))
        painter.drawText(x, y + cell - 2, path.stem[:44])
    painter.end()
    sheet.save(str(target), "PNG")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument(
        "--png", action="store_true", help="also write PNGs and a montage"
    )
    parser.add_argument("--arrangement", default="auto")
    args = parser.parse_args(argv)
    rows = run(args.out_dir, args.arrangement, args.png)
    passing = sum(1 for r in rows if r.passes)
    return 0 if passing >= PASS_TEMPLATES and not any(r.overlaps for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
