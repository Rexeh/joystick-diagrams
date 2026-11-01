"""Text-fit check over dense templates (spike S5 exit criterion; not a test module).

Five dense bundled templates are rendered with a synthetic device that binds
every control and gives each one **three modifiers**, under "Add them under the
main text" with colouring on, for Original (unchanged) and the Clean style. For
every slot that receives rich text the fit decision is recorded (fits at the
template size / shrunk / compact leading / truncated with ``+N more`` / does not
fit) and a summary is printed; the exit criterion is 95% of slots fitting.

Usage::

    uv run python -m tests.render.make_text_fit_check OUT_DIR [--png] [--verify]

``--png`` converts each SVG with the app's ``PngConverter`` (QtWebEngine,
offscreen). ``--verify`` loads each SVG in QtWebEngine and measures every
label's rendered text block with ``getBoundingClientRect`` — an independent
check of the width table against Chromium's own layout — and reports any label
wider than its wrapping width or taller than its box. Settings are patched to
defaults so the developer database is never touched.
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

from joystick_diagrams.export import _dom_binding_options
from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.modifier_identity import (
    ModifierDisplay,
    ModifierRegistrySnapshot,
)
from joystick_diagrams.render import (
    PipelineHooks,
    RenderContext,
    RenderJob,
    Theme,
    render_device,
    resolve_theme,
)
from joystick_diagrams.render.adapters._common import localname
from joystick_diagrams.render.binding import Run
from joystick_diagrams.render.modifier_presentation import (
    apply_modifier_presentation,
    fit_for_slot,
    painted_frames,
    slot_fit_box,
)
from joystick_diagrams.render.slot_fit import (
    AUTO_PADDING_PX,
    content_host,
    css_px,
    foreign_font,
    is_auto,
    plain_lines,
)
from joystick_diagrams.render.slots import TextTargetKind
from joystick_diagrams.render.style_writer import (
    apply_theme,
    parse_declarations,
    pin_light_colour_scheme,
)
from joystick_diagrams.render.text_fit import (
    DEFAULT_MIN_FONT_SIZE,
    HEIGHT_TOLERANCE_PX,
    line_em,
    line_width,
    wrap_line,
)
from joystick_diagrams.render.theme import CLEAN_THEME
from joystick_diagrams.template import Template
from tests.render.render_fixtures import REPO_ROOT, export_device_for, new_device

NOW = datetime(2026, 10, 20, 12, 0, 0)
PASS_RATE = 0.95
TOLERANCE_PX = HEIGHT_TOLERANCE_PX + 0.5  # the model's slack plus Chromium rounding

DENSE_TEMPLATES = (
    REPO_ROOT / "templates" / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg",
    REPO_ROOT / "templates" / "Virpil" / "Virpil Constellation ALPHA R.svg",
    REPO_ROOT
    / "templates"
    / "WinWing"
    / "Orion2 18 Throttle Combo"
    / "Orion2 18 Throttle Combo.svg",
    REPO_ROOT / "templates" / "Thrustmaster" / "Thrustmaster Warthog - Throttle.svg",
    REPO_ROOT / "templates" / "Saitek - Logitech" / "X56 H.O.T.A.S. Throttle.svg",
)

COMMANDS = (
    "Weapon release",
    "Target lock",
    "Countermeasures",
    "Zoom in",
    "Autopilot",
    "Landing gear",
    "Radar elevation up",
    "Master arm",
)
MODIFIERS = (
    ({"LShift"}, "Alt fire"),
    ({"RCtrl"}, "Master arm"),
    ({"lalt", "LShift"}, "Jettison stores"),
)


# ── Device ──


def _bind(device: Device_, control, index: int) -> None:
    device.create_input(control, COMMANDS[index % len(COMMANDS)])
    for keys, command in MODIFIERS:
        device.add_modifier_to_input(control, set(keys), command)


def dense_device(template: Template) -> Device_:
    """Every control the template offers, each with three modifiers."""
    device = new_device("Dense device")
    index = 0
    for token in sorted(template.get_template_buttons()):
        _bind(device, Button(int(token.split("_")[1])), index)
        index += 1
    for token in sorted(template.get_template_axis()):
        parts = token.upper().split("_")
        if parts[1] == "SLIDER" and len(parts) == 3 and parts[2].isdigit():
            _bind(device, AxisSlider(int(parts[2])), index)
        elif len(parts) == 2 and parts[1] in AxisDirection.__members__:
            _bind(device, Axis(AxisDirection[parts[1]]), index)
        index += 1
    for token in sorted(template.get_template_hats()):
        parts = token.upper().split("_")
        if parts[2] in HatDirection.__members__:
            _bind(device, Hat(int(parts[1]), HatDirection[parts[2]]), index)
        index += 1
    return device


LONG_COMMANDS = (
    "Fire",
    "Weapon release",
    "Target Management Switch - Up",
    "Countermeasures Management Switch - Aft (Programme 1)",
    "Display Management Switch - Forward",
    "Radar elevation up",
    "Speed Brake - Retract Fully",
    "Air Refuel Door Toggle",
    "Gun Trigger - Second Stage",
    "Nosewheel Steering Disengage / Air Refuel Disconnect",
    "Trim",
    "IFF interrogation mode 4 (hold)",
)
# One word wider than any bundled box, to exercise "never shortened".
UNBREAKABLE_COMMAND = "AN/ALE-47_Countermeasures_Dispenser_Programme_Select"


def _controls(template: Template) -> list:
    controls = []
    for token in sorted(template.get_template_buttons()):
        controls.append(Button(int(token.split("_")[1])))
    for token in sorted(template.get_template_axis()):
        parts = token.upper().split("_")
        if parts[1] == "SLIDER" and len(parts) == 3 and parts[2].isdigit():
            controls.append(AxisSlider(int(parts[2])))
        elif len(parts) == 2 and parts[1] in AxisDirection.__members__:
            controls.append(Axis(AxisDirection[parts[1]]))
    for token in sorted(template.get_template_hats()):
        parts = token.upper().split("_")
        if parts[2] in HatDirection.__members__:
            controls.append(Hat(int(parts[1]), HatDirection[parts[2]]))
    return controls


def long_device(template: Template, *, modifiers: bool = False) -> Device_:
    """Every control bound with long (synthetic) action names; the 7th control
    gets one unbreakable word. ``modifiers`` adds the three ``MODIFIERS`` and
    makes every fifth control modifier-only (one modifier, no plain binding)."""
    device = new_device("Long names")
    for index, control in enumerate(_controls(template)):
        if modifiers and index % 5 == 4:
            keys, mod_command = MODIFIERS[index % len(MODIFIERS)]
            device.add_modifier_to_input(control, set(keys), mod_command)
            continue
        command = (
            UNBREAKABLE_COMMAND
            if index == 6
            else LONG_COMMANDS[index % len(LONG_COMMANDS)]
        )
        device.create_input(control, command)
        if modifiers:
            for keys, mod_command in MODIFIERS:
                device.add_modifier_to_input(control, set(keys), mod_command)
    return device


# ── Recording hook ──


@dataclass
class SlotFit:
    key: str
    width: float | None
    height: float | None
    base_size: float
    font_size: float
    line_height: float
    lines: int
    truncated: int
    fits: bool
    margin_left: str | None = None  # outer flex div style, to find it in Chromium
    padding_top: str | None = None

    @property
    def shrunk(self) -> bool:
        return self.font_size < self.base_size

    @property
    def compact(self) -> bool:
        return self.line_height < 1.2


def _outer_style(div) -> tuple[str | None, str | None]:
    for ancestor in div.iterancestors():
        declarations = parse_declarations(ancestor.get("style"))
        if "width" in declarations:
            return declarations.get("margin-left"), declarations.get("padding-top")
    return None, None


class FitRecorder:
    """A style hook placed before the presentation hook: records every fit."""

    def __init__(self) -> None:
        self.fits: list[SlotFit] = []

    def __call__(self, job: RenderJob) -> None:
        assert job.slots is not None and job.doc is not None
        frames = painted_frames(job.doc.root)
        for slot in job.slots.slots:
            if len(slot.tokens) != 1:
                continue
            rich = job.resolver.rich_for(slot.key, 0)
            if rich is None or rich.is_plain:
                continue
            fit = fit_for_slot(job, slot, rich, frames)
            if fit is None:
                continue
            div = next(
                (
                    t.element
                    for t in slot.text_targets
                    if t.kind is TextTargetKind.FOREIGN_OBJECT
                ),
                None,
            )
            box = slot_fit_box(slot, div, frames, job.slots.offset)
            margin_left, padding_top = (
                _outer_style(div) if div is not None else (None, None)
            )
            self.fits.append(
                SlotFit(
                    slot.key,
                    box.width,
                    box.height,
                    fit.base_size,
                    fit.font_size,
                    fit.line_height,
                    len(fit.wrapped),
                    fit.truncated,
                    fit.fits,
                    margin_left,
                    padding_top,
                )
            )


# ── Checking what was written (pure measurement path) ──


@dataclass
class WrittenLabel:
    """A label read back from the rendered document and measured with the width
    table: independent of the ``FitResult`` that wrote it."""

    key: str
    text: str
    font_size: float
    line_height: float
    width: float | None
    height: float | None
    lines: int
    too_wide: bool
    too_tall: bool
    reported: bool  # listed in ``text_overflow``
    text_size: float | None  # the <text> fallback's font-size
    model_size: float | None  # the model cell's fontSize

    @property
    def overflows(self) -> bool:
        return self.too_wide or self.too_tall


def written_lines(div) -> tuple:
    """The lines a foreignObject block shows, with each line block's em size."""
    host = content_host(div)
    blocks = [c for c in host if isinstance(c.tag, str) and localname(c) == "div"]
    if not blocks:
        return plain_lines(host)
    lines = []
    for block in blocks:
        size = parse_declarations(block.get("style")).get("font-size", "")
        em = float(size[:-2]) if size.endswith("em") else None
        text = " ".join("".join(block.itertext()).split())
        if text:
            lines.append((Run(text, size_em=em),))
    return tuple(lines)


def measure_written(job: RenderJob, slot, frames) -> WrittenLabel | None:
    div = next(
        (
            t.element
            for t in slot.text_targets
            if t.kind is TextTargetKind.FOREIGN_OBJECT
        ),
        None,
    )
    if div is None:
        return None
    lines = written_lines(div)
    if not lines:
        return None
    font = foreign_font(div)
    line_height = css_px(parse_declarations(div.get("style")).get("line-height")) or 1.2
    box = slot_fit_box(slot, div, frames, job.slots.offset).inset(AUTO_PADDING_PX)
    wrapped = [w for line in lines for w in wrap_line(line, box.width, font)]
    too_wide = box.width is not None and any(
        line_width(w, font) > box.width + 0.01 for w in wrapped
    )
    height = sum(line_height * font.size * line_em(w) for w in wrapped)
    too_tall = (
        box.height is not None and height > box.height + HEIGHT_TOLERANCE_PX + 0.01
    )
    text_element = next(
        (t.element for t in slot.text_targets if t.kind is TextTargetKind.TEXT), None
    )
    text_size = (
        css_px(text_element.get("font-size")) if text_element is not None else None
    )
    model = slot.cell.style_dict.get("fontSize") if slot.cell is not None else None
    return WrittenLabel(
        slot.key,
        " / ".join("".join(r.text for r in line) for line in lines),
        font.size,
        line_height,
        box.width,
        box.height,
        len(wrapped),
        too_wide,
        too_tall,
        any(key == slot.key for key, _ in job.text_overflow),
        text_size,
        float(model) if model else None,
    )


class WrittenCheck:
    """A style hook placed after the presentation hook: measures every label that
    "Auto" fitted, as written."""

    def __init__(self) -> None:
        self.labels: list[WrittenLabel] = []

    def __call__(self, job: RenderJob) -> None:
        assert job.slots is not None and job.doc is not None
        frames = painted_frames(job.doc.root)
        for slot in job.slots.slots:
            if not is_auto(job, slot):
                continue
            label = measure_written(job, slot, frames)
            if label is not None:
                self.labels.append(label)


@dataclass
class AutoStats:
    template: str
    variant: str
    slots: int = 0
    grew: int = 0
    stayed: int = 0
    shrank: int = 0
    at_minimum: int = 0
    too_long: int = 0  # still too long at the minimum (reported, never shortened)
    truncated: int = 0  # modifier lines replaced by "+N more"


class FitLog:
    """Records every ``FitResult`` the presentation hook makes (patched in)."""

    def __init__(self) -> None:
        self.fits: list[tuple[str, object]] = []

    def wrap(self, real):
        def recording(job, slot, rich, frames=None, **kw):
            fit = real(job, slot, rich, frames, **kw)
            if fit is not None:
                self.fits.append((slot.key, fit))
            return fit

        return recording


def auto_stats(template: str, variant: str, fits, min_size: float) -> AutoStats:
    stats = AutoStats(template, variant)
    for _key, fit in fits:
        stats.slots += 1
        if fit.font_size > fit.base_size:
            stats.grew += 1
        elif fit.font_size == fit.base_size:
            stats.stayed += 1
        else:
            stats.shrank += 1
        if fit.font_size <= min_size:
            stats.at_minimum += 1
        if not fit.fits:
            stats.too_long += 1
        if fit.truncated:
            stats.truncated += 1
    return stats


AUTO_TEMPLATES = (
    REPO_ROOT / "templates" / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg",
    REPO_ROOT
    / "templates"
    / "WinWing"
    / "Orion2 18 Throttle Combo"
    / "Orion2 18 Throttle Combo.svg",
    REPO_ROOT / "templates" / "Thrustmaster" / "Thrustmaster Warthog - Throttle.svg",
)


def render_auto(path: Path, *, modifiers: bool, display: ModifierDisplay):
    """Render ``path`` with Clean ("Auto") and long bindings; returns
    ``(outcome, FitLog, WrittenCheck)``."""
    from joystick_diagrams.render import modifier_presentation

    template = Template(str(path))
    device = long_device(template, modifiers=modifiers)
    ed = export_device_for(template.raw_data, device, "Long names")
    ctx = RenderContext(
        theme=resolve_theme(CLEAN_THEME),
        colour_modifiers=True,
        registry=ModifierRegistrySnapshot.default(colouring_enabled=True),
        modifier_display=display,
        now=NOW,
        engine_override="dom",
    )
    log, check = FitLog(), WrittenCheck()
    hooks = PipelineHooks(
        style=(apply_theme, apply_modifier_presentation, check, pin_light_colour_scheme)
    )
    with patch.object(
        modifier_presentation,
        "fit_for_slot",
        log.wrap(modifier_presentation.fit_for_slot),
    ):
        outcome = render_device(ed, ctx, _dom_binding_options(ctx), hooks=hooks)
    return outcome, log, check


AUTO_VARIANTS = (
    ("plain", False, ModifierDisplay.TEMPLATE_BOXES),
    ("under_text", True, ModifierDisplay.UNDER_MAIN_TEXT),
)


def auto_report(out_dir: Path | None = None) -> list[AutoStats]:
    results = []
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        for path in AUTO_TEMPLATES:
            for name, modifiers, display in AUTO_VARIANTS:
                outcome, log, check = render_auto(
                    path, modifiers=modifiers, display=display
                )
                stats = auto_stats(path.stem, name, log.fits, DEFAULT_MIN_FONT_SIZE)
                results.append(stats)
                bad = [
                    lab for lab in check.labels if lab.overflows and not lab.reported
                ]
                print(
                    f"{path.stem} [{name}]: {stats.slots} fitted: grew {stats.grew}, "
                    f"stayed {stats.stayed}, shrank {stats.shrank}, at the minimum "
                    f"{stats.at_minimum}, too long {stats.too_long}, "
                    f"+N more {stats.truncated}; measured {len(check.labels)}, "
                    f"overflowing unreported {len(bad)}; report lists "
                    f"{len(outcome.report.text_overflow)}"
                )
                for lab in bad:
                    print(f"    UNREPORTED {lab}")
                if out_dir is not None:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    target = out_dir / f"{path.stem} - auto_{name}.svg"
                    target.write_text(outcome.svg_text, encoding="utf-8")
    return results


# ── Rendering ──


@dataclass(frozen=True)
class Variant:
    name: str
    theme: Theme | None

    def context(self) -> RenderContext:
        return RenderContext(
            theme=resolve_theme(self.theme),
            colour_modifiers=True,
            registry=ModifierRegistrySnapshot.default(colouring_enabled=True),
            modifier_display=ModifierDisplay.UNDER_MAIN_TEXT,
            now=NOW,
            engine_override="dom",
        )


VARIANTS = (
    Variant("original_under_text", None),
    Variant("clean_under_text", CLEAN_THEME),
)


@dataclass
class Result:
    template: str
    variant: str
    svg: Path
    fits: list[SlotFit]

    @property
    def summary(self) -> dict[str, int]:
        return {
            "slots": len(self.fits),
            "fit": sum(f.fits for f in self.fits),
            "at_template_size": sum(
                f.fits and not f.shrunk and not f.compact for f in self.fits
            ),
            "shrunk": sum(f.shrunk for f in self.fits),
            "compact": sum(f.compact for f in self.fits),
            "truncated": sum(bool(f.truncated) for f in self.fits),
            "overflow": sum(not f.fits for f in self.fits),
        }


def render_checks(out_dir: Path, templates=DENSE_TEMPLATES) -> list[Result]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[Result] = []
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        for path in templates:
            template = Template(str(path))
            device = dense_device(template)
            ed = export_device_for(template.raw_data, device, "Dense profile")
            for variant in VARIANTS:
                recorder = FitRecorder()
                hooks = PipelineHooks(
                    style=(
                        apply_theme,
                        recorder,
                        apply_modifier_presentation,
                        pin_light_colour_scheme,
                    )
                )
                ctx = variant.context()
                outcome = render_device(ed, ctx, _dom_binding_options(ctx), hooks=hooks)
                target = out_dir / f"{path.stem} - {variant.name}.svg"
                target.write_text(outcome.svg_text, encoding="utf-8")
                results.append(Result(path.stem, variant.name, target, recorder.fits))
    return results


def print_summary(results: list[Result]) -> float:
    total = sum(len(r.fits) for r in results)
    fitting = sum(r.summary["fit"] for r in results)
    for result in results:
        s = result.summary
        print(
            f"{result.template} [{result.variant}]: {s['fit']}/{s['slots']} fit "
            f"(template size {s['at_template_size']}, shrunk {s['shrunk']}, "
            f"compact {s['compact']}, truncated {s['truncated']}, overflow {s['overflow']})"
        )
        for f in result.fits:
            if not f.fits:
                print(
                    f"    overflow: {f.key} box={f.width}x{f.height} size={f.font_size}"
                )
    rate = fitting / total if total else 1.0
    print(
        f"TOTAL: {fitting}/{total} slots fit ({rate:.1%}); exit criterion {PASS_RATE:.0%}"
    )
    return rate


# ── Chromium verification ──

_MEASURE_JS = """
(function () {
  const out = [];
  document.querySelectorAll('foreignObject > div').forEach((outer) => {
    let inner = outer;
    while (inner.firstElementChild && inner.firstElementChild.tagName.toLowerCase() === 'div') {
      inner = inner.firstElementChild;
    }
    const r = inner.getBoundingClientRect();
    out.push({
      ml: outer.style.marginLeft, pt: outer.style.paddingTop, w: parseFloat(outer.style.width),
      iw: r.width, ih: r.height, text: inner.textContent.slice(0, 60),
    });
  });
  return JSON.stringify(out);
})()
"""


def _measure_in_chromium(view, svg: Path) -> list[dict]:
    from PySide6.QtCore import QEventLoop, QSize, QTimer, QUrl

    from joystick_diagrams.export_image import parse_svg_dimensions

    width, height = parse_svg_dimensions(svg)
    view.setFixedSize(QSize(width, height))
    loop = QEventLoop()
    view.loadFinished.connect(loop.quit)
    view.load(QUrl.fromLocalFile(str(svg.resolve())))
    QTimer.singleShot(15000, loop.quit)
    loop.exec()
    view.loadFinished.disconnect(loop.quit)
    result: list[dict] = []
    done = QEventLoop()

    def on_result(value):
        result.extend(json.loads(value) if value else [])
        done.quit()

    view.page().runJavaScript(_MEASURE_JS, on_result)
    QTimer.singleShot(15000, done.quit)
    done.exec()
    return result


def verify(results: list[Result]) -> int:
    """Compare Chromium's text block sizes with the boxes; return the mismatch count."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication.instance() or QApplication(sys.argv)
    view = QWebEngineView()
    view.move(-10000, -10000)
    view.show()
    mismatches = 0
    for result in results:
        measured = {
            (m["ml"], m["pt"]): m for m in _measure_in_chromium(view, result.svg)
        }
        checked = 0
        for fit in result.fits:
            m = measured.get((fit.margin_left, fit.padding_top))
            if m is None or not fit.fits:
                continue
            checked += 1
            too_wide = m["w"] and m["iw"] > m["w"] + TOLERANCE_PX
            too_tall = fit.height is not None and m["ih"] > fit.height + TOLERANCE_PX
            if too_wide or too_tall:
                mismatches += 1
                print(
                    f"    MISMATCH {result.template} [{result.variant}] {fit.key}: "
                    f"chromium {m['iw']:.1f}x{m['ih']:.1f} vs box {m['w']}x{fit.height} "
                    f"at {fit.font_size}px lh={fit.line_height} ({m['text']!r})"
                )
        print(
            f"{result.template} [{result.variant}]: {checked} labels measured in Chromium"
        )
    view.close()
    view.deleteLater()
    app.processEvents()
    print(f"VERIFY: {mismatches} label(s) exceed their box in Chromium")
    return mismatches


def convert_to_png(svg_paths: list[Path]) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from joystick_diagrams.export_image import PngConverter

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication.instance() or QApplication(sys.argv)
    jobs: list[tuple[str, str]] = []
    for svg in svg_paths:
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
    parser.add_argument(
        "--verify", action="store_true", help="measure labels in Chromium"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help='only the "Auto" report (Clean, long bindings, three templates)',
    )
    args = parser.parse_args(argv)
    if args.auto:
        auto_report(args.out_dir)
        return 0
    results = render_checks(args.out_dir)
    rate = print_summary(results)
    (args.out_dir / "text_fit_results.json").write_text(
        json.dumps(
            [
                {
                    "template": r.template,
                    "variant": r.variant,
                    **r.summary,
                    "slots_detail": [asdict(f) for f in r.fits],
                }
                for r in results
            ],
            indent=1,
        ),
        encoding="utf-8",
    )
    mismatches = verify(results) if args.verify else 0
    if args.png:
        convert_to_png([r.svg for r in results])
    return 0 if rate >= PASS_RATE and mismatches == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
