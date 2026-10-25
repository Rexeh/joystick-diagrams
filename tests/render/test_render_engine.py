"""Engine selection, fallback and the export.py dispatch."""

import logging
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from unittest.mock import patch

import pytest

from joystick_diagrams.export import (
    MERGE_MODIFIERS_SETTING_KEY,
    export_device_to_templates,
    populate_template,
    render_template,
)
from joystick_diagrams.input.button import Button
from joystick_diagrams.render import (
    RENDER_ENGINE_SETTING_KEY,
    Engine,
    RenderContext,
    RenderNotice,
    build_render_context,
    choose_engine,
)
from tests.render.render_fixtures import (
    CellSpec,
    DrawioFixture,
    basic_fixture,
    build_svg,
    export_device_for,
    new_device,
)

NOW = datetime(2026, 1, 2)


def simple_device():
    dev = new_device()
    dev.create_input(Button(1), "Fire")
    dev.add_modifier_to_input(Button(1), {"ctrl"}, "Alt Fire")
    return dev


def setting(values: dict):
    return patch(
        "joystick_diagrams.db.db_settings.get_setting",
        side_effect=values.get,
    )


# ── choose_engine ──


def test_default_context_is_legacy_even_with_mock_template():
    ed = export_device_for("BUTTON_1", simple_device())  # MockTemplate: no template_key
    assert choose_engine(RenderContext(), ed) is Engine.LEGACY


@pytest.mark.parametrize(
    "ctx",
    [
        RenderContext(engine_override="dom"),
        RenderContext(theme=object()),
        RenderContext(colour_modifiers=True),
    ],
)
def test_opt_ins_select_dom(ctx):
    assert (
        choose_engine(ctx, export_device_for("BUTTON_1", simple_device())) is Engine.DOM
    )


def test_layout_ops_select_dom_only_for_matching_template_key():
    @dataclass
    class KeyedTemplate:
        raw_data: str
        template_key: str

    @dataclass
    class KeyedWrapper:
        profile_name: str
        profile_key: str

    @dataclass
    class ED:
        template: object
        profile_wrapper: object
        device: object

    layouts = MappingProxyType({("bundled:a.svg", "", "dcs_p1"): ["move"]})
    ctx = RenderContext(layouts=layouts)
    ed = ED(
        KeyedTemplate("x", "bundled:a.svg"),
        KeyedWrapper("p1", "dcs_p1"),
        simple_device(),
    )
    assert choose_engine(ctx, ed) is Engine.DOM
    other = ED(
        KeyedTemplate("x", "bundled:b.svg"),
        KeyedWrapper("p1", "dcs_p1"),
        simple_device(),
    )
    assert choose_engine(ctx, other) is Engine.LEGACY
    assert choose_engine(ctx, export_device_for("x", simple_device())) is Engine.LEGACY


def test_legacy_override_beats_opt_ins():
    ctx = RenderContext(theme=object(), colour_modifiers=True, engine_override="legacy")
    assert choose_engine(ctx, export_device_for("x", simple_device())) is Engine.LEGACY


# ── build_render_context (hidden setting, label snapshot) ──


def test_build_render_context_reads_hidden_setting_at_call_time():
    with setting({RENDER_ENGINE_SETTING_KEY: "DOM"}):
        ctx = build_render_context(now=NOW)
    assert ctx.engine_override == "dom"
    assert ctx.now == NOW
    assert ctx.labels is None  # no AppState in tests
    assert build_render_context().engine_override is None


# ── render_template dispatch ──


def test_render_template_without_context_is_populate_template():
    ed = export_device_for("BUTTON_1 | BUTTON_1_Modifiers", simple_device())
    outcome = render_template(ed, None)
    assert outcome.svg_text == populate_template(ed)
    assert outcome.report.engine is Engine.LEGACY


def test_render_template_legacy_is_byte_identical_to_populate_template():
    text = build_svg(basic_fixture())
    ed = export_device_for(text, simple_device())
    legacy = populate_template(ed, now=NOW)
    outcome = render_template(ed, RenderContext(now=NOW))
    assert outcome.svg_text == legacy
    assert outcome.report.engine is Engine.LEGACY


def test_render_template_dom_path_runs_and_reports():
    ed = export_device_for(build_svg(basic_fixture("cellid")), simple_device())
    outcome = render_template(ed, RenderContext(engine_override="dom", now=NOW))
    assert outcome.report.engine is Engine.DOM
    assert outcome.report.adapter == "drawio_cell_id"
    assert outcome.report.notices == ()
    assert "Fire" in outcome.svg_text


def test_non_xml_template_falls_back_with_warning(caplog):
    ed = export_device_for("BUTTON_1 | BUTTON_1_Modifiers", simple_device())
    with caplog.at_level(logging.WARNING, logger="joystick_diagrams.export"):
        outcome = render_template(ed, RenderContext(engine_override="dom", now=NOW))
    assert outcome.report.engine is Engine.LEGACY
    assert RenderNotice.PARSE_ERROR in outcome.report.notices
    assert RenderNotice.FELL_BACK_TO_LEGACY in outcome.report.notices
    assert outcome.svg_text == populate_template(ed, now=NOW)
    assert any(
        "fell back to legacy" in r.message and "parse_error" in r.message
        for r in caplog.records
    )


def test_generic_svg_falls_back_as_not_drawio(caplog):
    text = '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"><text>BUTTON_1</text></svg>'
    ed = export_device_for(text, simple_device())
    with caplog.at_level(logging.WARNING, logger="joystick_diagrams.export"):
        outcome = render_template(ed, RenderContext(engine_override="dom", now=NOW))
    assert outcome.report.engine is Engine.LEGACY
    assert RenderNotice.NOT_DRAWIO in outcome.report.notices
    assert "Fire" in outcome.svg_text
    assert any("not_drawio" in r.message for r in caplog.records)


def test_token_in_attribute_triggers_coverage_fallback(caplog):
    text = build_svg(basic_fixture()).replace("<defs/>", '<defs id="BUTTON_1"/>')
    ed = export_device_for(text, simple_device())
    with caplog.at_level(logging.WARNING, logger="joystick_diagrams.export"):
        outcome = render_template(ed, RenderContext(engine_override="dom", now=NOW))
    assert RenderNotice.COVERAGE_MISMATCH in outcome.report.notices
    assert outcome.svg_text == populate_template(ed, now=NOW)
    assert any("coverage_mismatch" in r.message for r in caplog.records)


def test_token_in_comment_does_not_trigger_fallback():
    text = build_svg(basic_fixture()).replace(
        "<defs/>", "<defs/><!-- BUTTON_1 here -->"
    )
    ed = export_device_for(text, simple_device())
    outcome = render_template(ed, RenderContext(engine_override="dom", now=NOW))
    assert outcome.report.engine is Engine.DOM
    assert "<!-- BUTTON_1 here -->" in outcome.svg_text


def test_unexpected_exception_falls_back(caplog):
    ed = export_device_for(build_svg(basic_fixture()), simple_device())
    with (
        patch(
            "joystick_diagrams.export.render_device", side_effect=RuntimeError("boom")
        ),
        caplog.at_level(logging.WARNING, logger="joystick_diagrams.export"),
    ):
        outcome = render_template(ed, RenderContext(engine_override="dom", now=NOW))
    assert RenderNotice.UNEXPECTED_ERROR in outcome.report.notices
    assert outcome.svg_text == populate_template(ed, now=NOW)
    assert any("boom" in r.message for r in caplog.records)


def test_dom_path_honours_merge_setting_snapshotted_in_context():
    """The "Showing modifiers" choice travels in the RenderContext (plan §1.4):
    the legacy ``merge_modifiers_into_input`` key migrates to MERGED_SAME_LINE."""
    ed = export_device_for(build_svg(basic_fixture()), simple_device())
    with setting(
        {MERGE_MODIFIERS_SETTING_KEY: "true", RENDER_ENGINE_SETTING_KEY: "dom"}
    ):
        ctx = build_render_context(now=NOW)
    outcome = render_template(ed, ctx)
    assert outcome.report.engine is Engine.DOM
    assert "Fire | Alt Fire - ctrl" in outcome.svg_text


def test_dom_path_ignores_setting_changes_after_context_was_built():
    ed = export_device_for(build_svg(basic_fixture()), simple_device())
    ctx = RenderContext(engine_override="dom", now=NOW)
    with setting({MERGE_MODIFIERS_SETTING_KEY: "true"}):
        outcome = render_template(ed, ctx)
    assert "Fire | Alt Fire - ctrl" not in outcome.svg_text


def test_hidden_setting_drives_export_end_to_end(tmp_path):
    @dataclass
    class ED:
        template: object
        profile_wrapper: object
        device: object
        device_id: str = "666ec0a0-556b-11ee-8002-444553540000"

    inner = export_device_for(build_svg(basic_fixture()), simple_device())
    ed = ED(inner.template, inner.profile_wrapper, inner.device)
    with (
        setting({RENDER_ENGINE_SETTING_KEY: "dom"}),
        patch("joystick_diagrams.export.render_template", wraps=render_template) as spy,
    ):
        result = export_device_to_templates(
            ed, tmp_path, "SVG", build_render_context(now=NOW)
        )
    assert result is not None
    assert spy.call_args.args[1].engine_override == "dom"
    written = (tmp_path / f"{ed.device_id[:5]}-Test Device-profile_1.svg").read_text(
        encoding="utf-8"
    )
    assert "Fire" in written
    assert written.startswith('<?xml version="1.0" encoding="UTF-8"?>')


def test_export_builds_context_when_none_given(tmp_path):
    @dataclass
    class ED:
        template: object
        profile_wrapper: object
        device: object
        device_id: str = "666ec0a0-556b-11ee-8002-444553540000"

    inner = export_device_for(
        build_svg(DrawioFixture(cells=[CellSpec("b", "BUTTON_1")])), simple_device()
    )
    ed = ED(inner.template, inner.profile_wrapper, inner.device)
    from joystick_diagrams.export import export

    svg_path, png_path = export(ed, str(tmp_path), "SVG")
    assert png_path is None
    assert "Fire" in open(svg_path, encoding="utf-8").read()
