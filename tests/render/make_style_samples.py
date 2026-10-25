"""Render review samples for the style/modifier work (not a test module).

Three bundled templates are rendered with a synthetic device that carries
modifier binds (``LShift``, ``RCtrl``, ``lalt``, ``JOY_BTN3`` and a qualifier)
under three settings:

- ``original``: Original (unchanged), colouring off, modifiers in template boxes
  (the legacy regex engine, byte-identical to today);
- ``clean_under_text``: Clean style, modifiers under the main text, coloured;
- ``high_contrast_boxes``: High contrast style, template boxes, coloured
  (Starter Template has one modifier box on Button_1, so it shows ``+2 more``).

Usage::

    uv run python -m tests.render.make_style_samples OUT_DIR [--png]

``--png`` converts each SVG with the app's ``PngConverter`` (QtWebEngine,
offscreen). Settings are patched to defaults so the developer database is never
touched.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from joystick_diagrams.export import render_template
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.modifier import ModifierKind
from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    ModifierRegistrySnapshot,
)
from joystick_diagrams.render import RenderContext, Theme, resolve_theme
from joystick_diagrams.render.theme import CLEAN_THEME, HIGH_CONTRAST_THEME
from joystick_diagrams.template import Template
from tests.render.render_fixtures import (
    REPO_ROOT,
    export_device_for,
    synthetic_device,
)

NOW = datetime(2026, 10, 20, 12, 0, 0)

SAMPLE_TEMPLATES = (
    REPO_ROOT / "templates" / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg",
    REPO_ROOT / "templates" / "Virpil" / "Virpil Constellation ALPHA R.svg",
    REPO_ROOT / "templates" / "Starter Template.svg",
)


@dataclass(frozen=True)
class Variant:
    name: str
    theme: Theme | None
    colouring: bool
    display: ModifierDisplay

    def context(self) -> RenderContext:
        registry = ModifierRegistrySnapshot.default(colouring_enabled=self.colouring)
        return RenderContext(
            theme=resolve_theme(self.theme),
            colour_modifiers=self.colouring,
            registry=registry,
            modifier_display=self.display,
            now=NOW,
        )


VARIANTS = (
    Variant("original", None, False, ModifierDisplay.TEMPLATE_BOXES),
    Variant("clean_under_text", CLEAN_THEME, True, ModifierDisplay.UNDER_MAIN_TEXT),
    Variant(
        "high_contrast_boxes", HIGH_CONTRAST_THEME, True, ModifierDisplay.TEMPLATE_BOXES
    ),
)


def sample_device(template: Template) -> Device_:
    """The parity suite's synthetic device plus a spread of modifier binds."""
    device = synthetic_device(template)
    buttons = sorted(
        (int(t.split("_")[1]) for t in template.get_template_buttons()), key=int
    )
    if not buttons:
        return device
    first = Button(buttons[0])
    device.create_input(first, "Weapon release")
    device.add_modifier_to_input(first, {"LShift"}, "Gun arm")
    device.add_modifier_to_input(first, {"RCtrl"}, "Master arm")
    device.add_modifier_to_input(first, {"lalt", "LShift"}, "Jettison stores")
    for number, (keys, command, kind) in zip(
        buttons[1:6],
        (
            ({"RCtrl"}, "Target lock", ModifierKind.KEY),
            ({"lalt"}, "Zoom in", ModifierKind.KEY),
            ({"JOY_BTN3"}, "Countermeasures", ModifierKind.KEY),
            ({"Long"}, "Eject", ModifierKind.QUALIFIER),
            ({"LShift", "RCtrl"}, "Autopilot", ModifierKind.KEY),
        ),
        strict=False,
    ):
        button = Button(number)
        device.create_input(button, f"Action {number}")
        device.add_modifier_to_input(button, set(keys), command, kind=kind)
    return device


def render_samples(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        for path in SAMPLE_TEMPLATES:
            template = Template(str(path))
            device = sample_device(template)
            ed = export_device_for(template.raw_data, device, "Sample profile")
            for variant in VARIANTS:
                outcome = render_template(ed, variant.context())
                target = out_dir / f"{path.stem} - {variant.name}.svg"
                target.write_text(outcome.svg_text, encoding="utf-8")
                written.append(target)
                print(
                    f"{target.name}: engine={outcome.report.engine.value} "
                    f"adapter={outcome.report.adapter} caps={sorted(c.value for c in outcome.report.capabilities)} "
                    f"notices={[n.value for n in outcome.report.notices]} overflow={dict(outcome.report.overflow)}"
                )
    return written


def convert_to_png(svg_paths: list[Path]) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from joystick_diagrams.export_image import PngConverter

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication.instance() or QApplication(sys.argv)
    jobs: list[tuple[str, str]] = []
    for svg in svg_paths:
        # PngConverter deletes its input SVG; convert a copy so the SVG sample stays.
        scratch = svg.with_suffix(".png.svg")
        shutil.copyfile(svg, scratch)
        jobs.append((str(scratch), str(svg.with_suffix(".png"))))
    converter = PngConverter(jobs)
    converter.finished.connect(app.quit)
    converter.start()
    app.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--png", action="store_true", help="also write PNGs")
    args = parser.parse_args(argv)
    written = render_samples(args.out_dir)
    if args.png:
        convert_to_png(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
