"""DOM engine throughput: 50 profiles x 5 devices = 250 renders (plan §1.6).

Runs only when selected explicitly (``uv run pytest -m perf -s``); the result is
recorded as a property and printed, and only a generous ceiling is asserted.
"""

import time
from datetime import datetime

import pytest

from joystick_diagrams.export import render_template
from joystick_diagrams.render import Engine, RenderContext
from joystick_diagrams.template import Template
from tests.render.render_fixtures import REPO_ROOT, export_device_for, synthetic_device

pytestmark = pytest.mark.perf

TEMPLATES = REPO_ROOT / "templates"
PERF_TEMPLATES = [
    TEMPLATES
    / "WinWing/URSA MINOR Fighter Joystick/URSA MINOR Fighter Joystick L - Button POV.svg",
    TEMPLATES
    / "WinWing/URSA MINOR Fighter Joystick/URSA MINOR Fighter Joystick R - Axis POV.svg",
    TEMPLATES / "Saitek - Logitech/X56 H.O.T.A.S. Throttle.svg",
    TEMPLATES / "Virpil/Virpil Constellation ALPHA L.svg",
    TEMPLATES / "Starter Template.svg",
]
PROFILES = 50
CEILING_SECONDS = 60.0


@pytest.fixture(autouse=True)
def _only_when_selected(request):
    if "perf" not in (request.config.getoption("-m") or ""):
        pytest.skip("perf tests run with -m perf")


def test_250_dom_renders(record_property):
    templates = [Template(str(path)) for path in PERF_TEMPLATES]
    devices = [
        export_device_for(t.raw_data, synthetic_device(t), "Perf") for t in templates
    ]
    ctx = RenderContext(engine_override="dom", now=datetime(2026, 1, 2))

    start = time.perf_counter()
    renders = 0
    for _profile in range(PROFILES):
        for ed in devices:
            outcome = render_template(ed, ctx)
            assert outcome.report.engine is Engine.DOM
            renders += 1
    elapsed = time.perf_counter() - start

    record_property("dom_renders", renders)
    record_property("dom_render_seconds", round(elapsed, 3))
    print(
        f"\n[perf] {renders} DOM renders in {elapsed:.2f}s "
        f"({elapsed / renders * 1000:.1f} ms/render, {len(templates)} templates x {PROFILES} profiles)"
    )
    assert renders == 250
    assert elapsed < CEILING_SECONDS
