"""Page exports reach the other apps: one ExportResult(kind="page") per page file."""
# ruff: noqa: F811 (pytest fixtures imported from tests/ui/stage34_fixtures.py)

import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.plugins.output_plugin_interface import (  # noqa: E402
    KIND_CONTROLLER,
    KIND_PAGE,
    ExportResult,
)
from joystick_diagrams.render.page import ProfileRule  # noqa: E402
from tests.ui.stage34_fixtures import (  # noqa: E402, F401
    STICK,
    THROTTLE,
    _reset_app_state,
    seed_state,
    settings_store,
)


def _run(qapp, job):
    from joystick_diagrams.ui.export_page import ExportDispatch

    worker = ExportDispatch(job)
    outcomes = []
    worker.signals.finished.connect(outcomes.append)
    worker.run()
    qapp.processEvents()
    return outcomes[0]


def _job(state, tmp_path, fmt, rule=ProfileRule.SHARED, with_devices=True):
    from joystick_diagrams.export import page_profiles
    from joystick_diagrams.ui.device_setup_controller import get_export_devices
    from joystick_diagrams.ui.export_page import ExportJob

    page = state.page_service.create(
        "Stick + Throttle", [STICK, THROTTLE], profile_rule=rule
    )
    devices = list(get_export_devices())
    pages = [(page, wrapper) for wrapper in page_profiles(page, devices)]
    ready = [d for d in devices if d.has_template] if with_devices else []
    job = ExportJob(ready, pages, devices, Path(tmp_path), fmt)
    return page, job


@pytest.mark.uitest
def test_page_export_produces_page_results(qapp, settings_store, tmp_path):
    state = seed_state()
    page, job = _job(state, tmp_path, "PNG")
    outcome = _run(qapp, job)
    pages = [r for r in outcome.results if r.kind == KIND_PAGE]
    controllers = [r for r in outcome.results if r.kind == KIND_CONTROLLER]
    assert len(controllers) == len(job.devices)
    assert [r.profile_name for r in pages] == ["F-16C"]  # the only shared profile
    (result,) = pages
    assert result.is_page and result.page_name == "Stick + Throttle"
    assert result.device_name == "Stick + Throttle"
    assert result.device_guid == page.page_id
    assert result.template_name is None
    assert result.source_plugin == "DCS World"
    assert result.export_format == "PNG"
    assert result.file_path.suffix == ".png"
    assert result.export_directory == Path(tmp_path)
    assert [d.guid for d in result.devices] == [STICK, THROTTLE]
    assert result.device is result.devices[0]
    assert result.devices[0].get_combined_inputs()  # this profile's bindings
    # Controller results are unchanged
    for item in controllers:
        assert item.devices == () and item.page_name is None
        assert item.template_name


@pytest.mark.uitest
def test_page_results_follow_the_svg_and_pdf_rule(qapp, settings_store, tmp_path):
    state = seed_state()
    _page, job = _job(state, tmp_path, "SVG", with_devices=False)
    (result,) = _run(qapp, job).results
    assert result.export_format == "SVG" and result.file_path.suffix == ".svg"
    assert result.file_path.exists()


@pytest.mark.uitest
def test_any_rule_gives_an_empty_device_for_a_controller_without_bindings(
    qapp, settings_store, tmp_path
):
    state = seed_state()
    _page, job = _job(
        state, tmp_path / "out", "PDF", rule=ProfileRule.ANY, with_devices=False
    )
    results = {r.profile_name: r for r in _run(qapp, job).results}
    assert set(results) == {"F-16C", "A-10C", "Common"}
    a10 = results["A-10C"]
    assert a10.export_format == "PDF" and a10.file_path.suffix == ".pdf"
    stick, throttle = a10.devices
    assert stick.get_combined_inputs()
    assert throttle.guid == THROTTLE and not throttle.get_combined_inputs()


@pytest.mark.uitest
def test_page_results_are_sent_with_the_batch(qapp, settings_store, tmp_path):
    from joystick_diagrams.ui.export_page import OutputPluginDispatch

    state = seed_state()
    _page, job = _job(state, tmp_path, "PNG")
    outcome = _run(qapp, job)
    other_app = MagicMock()
    state.output_plugin_manager.get_enabled_plugin_wrappers.return_value = [other_app]
    OutputPluginDispatch(outcome.results).run()
    (batch,), _kwargs = other_app.run.call_args
    assert any(r.kind == KIND_PAGE for r in batch)
    assert batch == outcome.results


def test_old_style_consumer_reads_page_results_unchanged(tmp_path):
    """A plugin written before pages (OpenKneeboard style: PNGs by profile)."""
    from joystick_diagrams.input.device import Device_

    png = tmp_path / "Stick + Throttle - F-16C.png"
    png.write_bytes(b"png")
    stick = Device_(STICK, "Gladiator NXT")
    throttle = Device_(THROTTLE, "Warthog Throttle")
    positional = ExportResult(
        "F-16C",
        "Gladiator NXT",
        STICK,
        "DCS World",
        "stick.svg",
        "SVG",
        tmp_path / "x.svg",
        tmp_path,
        stick,
    )
    assert positional.kind == KIND_CONTROLLER and positional.devices == ()
    page = ExportResult(
        profile_name="F-16C",
        device_name="Stick + Throttle",
        device_guid="page_1",
        source_plugin="DCS World",
        template_name=None,
        export_format="PNG",
        file_path=png,
        export_directory=tmp_path,
        device=stick,
        kind=KIND_PAGE,
        page_name="Stick + Throttle",
        devices=(stick, throttle),
    )

    def old_consumer(results, root: Path) -> list[Path]:
        copied = []
        for result in [r for r in results if r.export_format == "PNG"]:
            target = root / result.profile_name
            target.mkdir(parents=True, exist_ok=True)
            copied.append(Path(shutil.copy2(result.file_path, target)))
            assert result.device.name  # still a controller
        return copied

    copied = old_consumer([positional, page], tmp_path / "kneeboard")
    assert copied == [tmp_path / "kneeboard" / "F-16C" / png.name]
