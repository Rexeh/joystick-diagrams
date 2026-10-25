"""RenderContext layout layers, engine selection with/without ops, editor entry point."""

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from unittest.mock import patch

from lxml import etree

from joystick_diagrams.export import populate_template, render_template
from joystick_diagrams.input.button import Button
from joystick_diagrams.render import (
    Engine,
    RenderContext,
    build_render_context,
    choose_engine,
)
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.drawio_model import DrawioModel
from joystick_diagrams.render.editor import (
    EditorOptions,
    PlaceholderResolver,
    render_for_editor,
)
from joystick_diagrams.render.layout import HideOp, LayoutDocument, LayoutLayers, MoveOp
from tests.render.render_fixtures import (
    basic_fixture,
    build_svg,
    new_device,
)

NOW = datetime(2026, 1, 2)


@dataclass
class KeyedTemplate:
    raw_data: str
    template_key: str = "bundled:a.svg"
    content_hash: str = "h"


@dataclass
class KeyedWrapper:
    profile_name: str
    profile_key: str


@dataclass
class ED:
    template: object
    profile_wrapper: object
    device: object


def device():
    dev = new_device()
    dev.create_input(Button(1), "Fire")
    return dev


def test_layers_for_and_has_layout_ops_use_template_and_profile_layers():
    template_doc = LayoutDocument(ops=[MoveOp(target="button_1", dx=1, dy=1)])
    profile_doc = LayoutDocument(ops=[HideOp(target="button_2")])
    ctx = RenderContext(
        layouts=MappingProxyType({("k", ""): template_doc, ("k", "p1"): profile_doc})
    )
    layers = ctx.layers_for("k", "p1")
    assert isinstance(layers, LayoutLayers)
    assert [type(op).__name__ for op in layers.all_ops()] == ["MoveOp", "HideOp"]
    assert ctx.layers_for("k", "other").profile.is_empty
    assert ctx.layers_for("missing", "p1").is_empty
    assert ctx.has_layout_ops("k", None) and ctx.has_layout_ops("k", "p1")
    assert not ctx.has_layout_ops("missing", "p1") and not ctx.has_layout_ops(
        None, "p1"
    )
    empty = RenderContext(layouts=MappingProxyType({("k", ""): LayoutDocument()}))
    assert not empty.has_layout_ops("k", "p1")


def test_engine_selection_with_and_without_layout_ops():
    ed = ED(KeyedTemplate("BUTTON_1"), KeyedWrapper("p1", "dcs_p1"), device())
    assert choose_engine(RenderContext(), ed) is Engine.LEGACY
    doc = LayoutDocument(ops=[MoveOp(target="button_1", dx=1, dy=1)])
    ctx = RenderContext(layouts=MappingProxyType({("bundled:a.svg", ""): doc}))
    assert choose_engine(ctx, ed) is Engine.DOM
    other = ED(
        KeyedTemplate("BUTTON_1", template_key="bundled:b.svg"),
        KeyedWrapper("p1", "dcs_p1"),
        device(),
    )
    assert choose_engine(ctx, other) is Engine.LEGACY
    profile_ctx = RenderContext(
        layouts=MappingProxyType({("bundled:a.svg", "dcs_p2"): doc})
    )
    assert choose_engine(profile_ctx, ed) is Engine.LEGACY  # another profile's layer


def test_render_template_legacy_is_byte_identical_without_layout_ops():
    text = build_svg(basic_fixture())
    ed = ED(KeyedTemplate(text), KeyedWrapper("p1", "dcs_p1"), device())
    ctx = RenderContext(
        now=NOW,
        layouts=MappingProxyType(
            {("bundled:other.svg", ""): LayoutDocument(ops=[HideOp(target="button_1")])}
        ),
    )
    outcome = render_template(ed, ctx)
    assert outcome.report.engine is Engine.LEGACY
    assert outcome.svg_text == populate_template(ed, now=NOW)


def test_render_template_applies_layout_ops_through_dom_engine():
    text = build_svg(basic_fixture())
    ed = ED(KeyedTemplate(text), KeyedWrapper("p1", "dcs_p1"), device())
    doc = LayoutDocument(ops=[HideOp(target="button_2")])
    ctx = RenderContext(
        now=NOW, layouts=MappingProxyType({("bundled:a.svg", "dcs_p1"): doc})
    )
    outcome = render_template(ed, ctx)
    assert outcome.report.engine is Engine.DOM
    assert 'data-jd-op="hide"' in outcome.svg_text
    root = etree.fromstring(outcome.svg_text.encode("utf-8"), make_parser())
    assert not DrawioModel.from_content(root.get("content")).cells_by_id()["b2"].visible


def test_build_render_context_snapshots_layouts_from_app_state():
    class FakeService:
        def snapshot(self):
            return MappingProxyType(
                {("k", ""): LayoutDocument(ops=[HideOp(target="b")])}
            )

    class FakeState:
        layout_service = FakeService()
        label_service = type("L", (), {"get_all_custom_labels": staticmethod(dict)})()
        modifier_key_service = None
        theme_service = None

    with (
        patch("joystick_diagrams.render.context.snapshot_registry") as registry,
        patch("joystick_diagrams.render.context.snapshot_theme", return_value=None),
        patch("joystick_diagrams.render.context.snapshot_labels", return_value=None),
        patch("joystick_diagrams.app_state.AppState") as app_state,
    ):
        registry.return_value.colouring_enabled = False
        app_state._inst = object()
        app_state.return_value = FakeState()
        ctx = build_render_context(now=NOW)
    assert ctx.has_layout_ops("k", None)


def test_placeholder_resolver_keeps_tokens_and_reports_no_modifiers():
    resolver = PlaceholderResolver("My profile")
    assert resolver.text_for("button_1") == "BUTTON_1"
    assert resolver.text_for("TEMPLATE_NAME") == "My profile"
    assert resolver.html_for("button_1_modifier_1") == "BUTTON_1_MODIFIER_1"
    assert resolver.modifier_count("button_1") == 0 and resolver.input_keys() == []


def test_render_for_editor_with_device_uses_bindings_and_default_layers_from_context():
    text = build_svg(basic_fixture())
    ed = ED(KeyedTemplate(text), KeyedWrapper("p1", "dcs_p1"), device())
    doc = LayoutDocument(ops=[HideOp(target="button_2")])
    ctx = RenderContext(now=NOW, layouts=MappingProxyType({("bundled:a.svg", ""): doc}))
    render = render_for_editor(ed.template, ed, options=EditorOptions(ctx=ctx))
    assert "Fire" in render.svg_text and 'data-jd-op="hide"' in render.svg_text
    assert next(s for s in render.slots if s.key == "button_2").hidden
    assert next(s for s in render.slots if s.key == "button_2").layer == "template"
    assert render.report is not None and render.report.engine is Engine.DOM


def test_render_for_editor_falls_back_gracefully_on_non_drawio():
    render = render_for_editor(
        KeyedTemplate(
            "<svg xmlns='http://www.w3.org/2000/svg'><text>BUTTON_1</text></svg>"
        ),
        None,
    )
    assert not render.supported and render.slots == []
    assert [n.code for n in render.notices] == ["layout_unsupported"]
    assert "BUTTON_1" in render.svg_text
