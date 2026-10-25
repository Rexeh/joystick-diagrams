"""Composing pages: layout maths, id prefixing, real templates pairwise, the rule."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest
from lxml import etree

from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.render.compose import (
    ComposeError,
    compose_page,
    device_has_bindings,
    member_devices_for_profile,
    page_profile_plan,
    prefix_ids,
    profiles_for_page,
    smallest_font_px,
    strip_drawio_footer,
)
from joystick_diagrams.render.context import RenderContext
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.page import (
    MM_PER_PT,
    MM_PER_PX,
    TITLE_BAND_MM,
    Arrangement,
    Orientation,
    Page,
    Placement,
    ProfileRule,
    SizePreset,
    grid_shape,
    layout_page,
    printed_pt,
)
from joystick_diagrams.template import Template
from tests.render.render_fixtures import synthetic_device

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "templates"
VKB = TEMPLATES / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg"  # 1159 × 807, flat
WARTHOG = (
    TEMPLATES / "Thrustmaster" / "Thrustmaster Warthog - Throttle.svg"
)  # 828 × 1169
STARTER = TEMPLATES / "Starter Template.svg"  # 1159 × 807, modifier boxes
WITH_IDS = (
    TEMPLATES / "Total Controls" / "Total Controls - Multi Function Button Box.svg"
)

SVG_NS = "http://www.w3.org/2000/svg"
GUID_A = "a1b2c3d4-0001-11ee-8001-444553540000"
GUID_B = "a1b2c3d4-0002-11ee-8002-444553540000"
GUID_C = "a1b2c3d4-0003-11ee-8003-444553540000"

_templates: dict[Path, Template] = {}


def template(path: Path) -> Template:
    if path not in _templates:
        _templates[path] = Template(str(path))
    return _templates[path]


@dataclass
class Wrapper:
    profile_name: str

    @property
    def profile_key(self) -> str:
        return f"dcs_{self.profile_name.lower()}"


def export_device(device: Device_, path: Path | None, wrapper: Wrapper) -> ExportDevice:
    ed = ExportDevice(device, None, wrapper)
    ed._template = template(path) if path is not None else None
    return ed


def bound_device(path: Path, guid: str, name: str) -> Device_:
    device = synthetic_device(template(path))
    device.guid = guid
    device.name = name
    return device


def empty_device(guid: str, name: str) -> Device_:
    return Device_(guid, name)


def two_member_page(**fields) -> Page:
    return Page(
        name="Stick + Throttle",
        placements=[Placement(device_guid=GUID_A), Placement(device_guid=GUID_B)],
        **fields,
    )


def parse(svg_text: str) -> etree._Element:
    return etree.fromstring(svg_text.encode("utf-8"), make_parser())


def mm(value: str) -> float:
    assert value.endswith("mm")
    return float(value[:-2])


# ── Layout maths ──


class TestLayoutMaths:
    def test_grid_shapes(self):
        assert grid_shape(Arrangement.SIDE_BY_SIDE, 3) == (1, 3)
        assert grid_shape(Arrangement.STACKED, 3) == (3, 1)
        assert grid_shape(Arrangement.GRID, 3) == (2, 2)
        assert grid_shape(Arrangement.GRID, 4) == (2, 2)
        assert grid_shape(Arrangement.GRID, 5) == (2, 3)

    def test_side_by_side_a4_is_landscape_and_fits_both(self):
        page = two_member_page()
        layout = layout_page(page, [(1159, 807), (828, 1169)])
        assert (layout.width_mm, layout.height_mm) == (297.0, 210.0)
        a, b = layout.panels
        assert a.mm_per_px == pytest.approx(b.mm_per_px)
        # aspect preserved
        assert a.width_mm / a.height_mm == pytest.approx(1159 / 807)
        assert b.width_mm / b.height_mm == pytest.approx(828 / 1169)
        # inside the margins, under the title band, separated by the gap
        assert a.x_mm >= page.margin_mm - 1e-6
        assert min(a.y_mm, b.y_mm) >= page.margin_mm + TITLE_BAND_MM - 1e-6
        assert b.x_mm + b.width_mm <= layout.width_mm - page.margin_mm + 1e-6
        assert max(a.y_mm + a.height_mm, b.y_mm + b.height_mm) <= (
            layout.height_mm - page.margin_mm + 1e-6
        )
        assert b.x_mm - (a.x_mm + a.width_mm) == pytest.approx(page.gap_mm, abs=1e-6)
        # width-bound on A4 landscape: the block spans the margins exactly and
        # is centred vertically under the title band
        assert a.x_mm == pytest.approx(page.margin_mm)
        assert b.x_mm + b.width_mm == pytest.approx(layout.width_mm - page.margin_mm)
        top = page.margin_mm + TITLE_BAND_MM
        block_h = max(a.y_mm + a.height_mm, b.y_mm + b.height_mm) - min(a.y_mm, b.y_mm)
        assert min(a.y_mm, b.y_mm) - top == pytest.approx(
            (layout.height_mm - page.margin_mm - top - block_h) / 2
        )

    def test_stacked_is_portrait(self):
        layout = layout_page(
            two_member_page(arrangement=Arrangement.STACKED), [(1159, 807), (1159, 807)]
        )
        assert (layout.width_mm, layout.height_mm) == (210.0, 297.0)
        a, b = layout.panels
        assert a.x_mm == pytest.approx(b.x_mm)
        assert b.y_mm - (a.y_mm + a.height_mm) == pytest.approx(6.0, abs=1e-6)

    def test_presets_and_explicit_orientation(self):
        letter = layout_page(
            two_member_page(size_preset=SizePreset.LETTER), [(100, 100), (100, 100)]
        )
        assert (letter.width_mm, letter.height_mm) == (279.4, 215.9)
        kneeboard = layout_page(
            two_member_page(
                size_preset=SizePreset.KNEEBOARD, orientation=Orientation.PORTRAIT
            ),
            [(100, 100), (100, 100)],
        )
        assert (kneeboard.width_mm, kneeboard.height_mm) == (139.7, 215.9)
        custom = layout_page(
            two_member_page(size_preset=SizePreset.CUSTOM, width_mm=300, height_mm=100),
            [(100, 100), (100, 100)],
        )
        assert (custom.width_mm, custom.height_mm) == (300, 100)

    def test_fit_to_content_is_natural_size(self):
        page = two_member_page(
            size_preset=SizePreset.FIT, show_title=False, show_date=False
        )
        layout = layout_page(page, [(1000, 500), (1000, 500)])
        assert layout.panels[0].mm_per_px == pytest.approx(MM_PER_PX)
        assert layout.width_mm == pytest.approx(2000 * MM_PER_PX + 2 * 10 + 6)
        assert layout.height_mm == pytest.approx(500 * MM_PER_PX + 2 * 10)
        assert layout.title_y_mm is None

    def test_scale_slider_shrinks_and_recentres(self):
        full = layout_page(two_member_page(), [(1000, 500), (1000, 500)])
        half = layout_page(two_member_page(scale=0.5), [(1000, 500), (1000, 500)])
        assert half.panels[0].mm_per_px == pytest.approx(full.panels[0].mm_per_px / 2)
        centre = lambda p: p.x_mm + p.width_mm / 2  # noqa: E731
        block_full = (centre(full.panels[0]) + centre(full.panels[1])) / 2
        block_half = (centre(half.panels[0]) + centre(half.panels[1])) / 2
        assert block_full == pytest.approx(block_half) == pytest.approx(297 / 2)

    def test_explicit_placement_wins(self):
        page = two_member_page()
        page.placements[1] = Placement(device_guid=GUID_B, x_mm=5, y_mm=7, scale=0.5)
        layout = layout_page(page, [(1000, 500), (1000, 500)])
        b = layout.panels[1]
        assert (b.x_mm, b.y_mm) == (5, 7)
        assert b.width_mm == pytest.approx(layout.panels[0].width_mm / 2)

    def test_grid_of_three(self):
        page = Page(
            name="Three",
            arrangement=Arrangement.GRID,
            placements=[Placement(device_guid=g) for g in (GUID_A, GUID_B, GUID_C)],
        )
        layout = layout_page(page, [(1159, 807)] * 3)
        a, b, c = layout.panels
        assert a.y_mm == pytest.approx(b.y_mm)
        assert c.y_mm > a.y_mm + a.height_mm
        assert layout.landscape

    def test_printed_pt(self):
        assert printed_pt(12, MM_PER_PT) == pytest.approx(12)
        assert printed_pt(8, 0.1) == pytest.approx(0.8 / MM_PER_PT)


# ── Id prefixing and footer removal ──


class TestPrefixIds:
    SVG = (
        (
            f'<svg xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<defs><clipPath id="clip-1"><rect/></clipPath>'
            '<linearGradient id="grad"/><symbol id="sym"/></defs>'
            "<style>#clip-1 {{ fill: red }} #grad, #sym {{ x: url(#grad) }} #clip-10 {{}}</style>"
            '<g clip-path="url(#clip-1)" fill="url( \'#grad\' )">'
            '<use xlink:href="#sym"/><use href="#sym"/><a href="#other"/>'
            '<rect style="fill: url(#grad); clip-path: url(#clip-1)"/></g></svg>'
        )
        .replace("{{", "{")
        .replace("}}", "}")
    )

    def test_every_reference_form_is_rewritten(self):
        root = parse(self.SVG)
        mapping = prefix_ids(root, "p1-")
        assert mapping == {"clip-1": "p1-clip-1", "grad": "p1-grad", "sym": "p1-sym"}
        text = etree.tostring(root, encoding="unicode")
        assert 'id="p1-clip-1"' in text and 'id="p1-grad"' in text
        assert 'clip-path="url(#p1-clip-1)"' in text
        assert "fill=\"url('#p1-grad')\"" in text
        assert 'xlink:href="#p1-sym"' in text and 'href="#p1-sym"' in text
        assert 'href="#other"' in text  # unknown targets untouched
        assert 'style="fill: url(#p1-grad); clip-path: url(#p1-clip-1)"' in text
        style = root.find(f"{{{SVG_NS}}}style").text
        assert "#p1-clip-1 {" in style and "#p1-grad, #p1-sym" in style
        assert "url(#p1-grad)" in style
        assert "#clip-10 {" in style  # prefix match on a longer id is not rewritten

    def test_no_ids_is_a_no_op(self):
        root = parse(f'<svg xmlns="{SVG_NS}"><g/></svg>')
        assert prefix_ids(root, "p1-") == {}

    def test_strip_footer_variants(self):
        for text in (
            "Text is not SVG - cannot display",
            "Viewer does not support full SVG 1.1",
        ):
            root = parse(
                f'<svg xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink"><g/>'
                '<switch><g requiredFeatures="x"/><a xlink:href="h"><text>'
                f"{text}</text></a></switch></svg>"
            )
            strip_drawio_footer(root)
            assert [c.tag for c in root] == [f"{{{SVG_NS}}}g"]
        # a label switch (foreignObject + text) is not a footer
        root = parse(
            f'<svg xmlns="{SVG_NS}"><switch><foreignObject/><text>x</text></switch></svg>'
        )
        strip_drawio_footer(root)
        assert len(root) == 1

    def test_smallest_font_px(self):
        root = parse(
            f'<svg xmlns="{SVG_NS}"><text font-size="12px"/>'
            '<g style="font-size: 0px"><div style="font-size: 9px; color: red"/></g>'
            '<text font-size="6pt"/></svg>'
        )
        assert smallest_font_px(root) == pytest.approx(8.0)  # 6pt = 8px
        assert smallest_font_px(parse(f'<svg xmlns="{SVG_NS}"/>')) is None


# ── Real templates ──


PAIRS = [
    pytest.param(VKB, WARTHOG, id="vkb+warthog"),
    pytest.param(VKB, STARTER, id="vkb+starter"),
    pytest.param(WARTHOG, STARTER, id="warthog+starter"),
]


def _compose_pair(first: Path, second: Path, ctx, **page_fields):
    wrapper = Wrapper("F-16C_50")
    devices = {
        GUID_A: export_device(bound_device(first, GUID_A, "First"), first, wrapper),
        GUID_B: export_device(bound_device(second, GUID_B, "Second"), second, wrapper),
    }
    page = two_member_page(**page_fields)
    return compose_page(page, wrapper, devices, ctx), page


class TestComposeRealTemplates:
    @pytest.mark.parametrize(("first", "second"), PAIRS)
    def test_pairwise_side_by_side(self, first, second):
        result, page = _compose_pair(
            first, second, RenderContext(now=datetime(2026, 10, 25))
        )
        root = parse(result.svg_text)
        # root sized in mm, A4 landscape
        assert (root.get("width"), root.get("height")) == ("297mm", "210mm")
        assert root.get("viewBox") == "0 0 297 210"
        assert root.find(f"{{{SVG_NS}}}title").text == "F-16C_50 · Stick + Throttle"
        # no draw.io model anywhere; two nested panels with viewBoxes
        assert all(e.get("content") is None for e in root.iter())
        nested = root.findall(f".//{{{SVG_NS}}}svg")
        assert len(nested) == 2
        assert nested[0].get("viewBox").split()[2:] == ["1159", "807"] or first != VKB
        for panel in nested:
            assert panel.get("preserveAspectRatio") == "xMidYMid meet"
            assert mm(root.get("width")) >= float(panel.get("x")) + float(
                panel.get("width")
            )
        # positions follow the layout maths
        layout = layout_page(
            page,
            [
                tuple(float(v) for v in panel.get("viewBox").split()[2:])
                for panel in nested
            ],
        )
        for panel, box in zip(nested, layout.panels, strict=True):
            assert float(panel.get("x")) == pytest.approx(box.x_mm, abs=1e-3)
            assert float(panel.get("y")) == pytest.approx(box.y_mm, abs=1e-3)
            assert float(panel.get("width")) == pytest.approx(box.width_mm, abs=1e-3)
        # ids unique
        ids = [e.get("id") for e in root.iter() if e.get("id")]
        assert len(ids) == len(set(ids))
        # footers gone, bindings present, title and date present
        assert "Text is not SVG" not in result.svg_text
        assert "Viewer does not support" not in result.svg_text
        assert "cmd button" in result.svg_text
        assert "25/10/2026" in result.svg_text
        assert result.empty_members == ()
        assert result.rendered_members == (GUID_A, GUID_B)
        assert result.min_font_pt is not None
        assert (result.width_mm, result.height_mm) == (297.0, 210.0)

    def test_dom_engine_path(self):
        result, _ = _compose_pair(VKB, STARTER, RenderContext(engine_override="dom"))
        assert all(
            p.report is not None and p.report.engine.value == "dom"
            for p in result.panels
        )
        assert "Text is not SVG" not in result.svg_text
        root = parse(result.svg_text)
        assert len(root.findall(f".//{{{SVG_NS}}}svg")) == 2

    def test_legacy_default_without_context(self):
        result, _ = _compose_pair(VKB, WARTHOG, None)
        assert all(p.report.engine.value == "legacy" for p in result.panels)

    def test_same_template_twice_keeps_ids_and_references_distinct(self):
        wrapper = Wrapper("F-16C_50")
        devices = {
            GUID_A: export_device(
                bound_device(WITH_IDS, GUID_A, "Left"), WITH_IDS, wrapper
            ),
            GUID_B: export_device(
                bound_device(WITH_IDS, GUID_B, "Right"), WITH_IDS, wrapper
            ),
        }
        result = compose_page(two_member_page(), wrapper, devices, None)
        root = parse(result.svg_text)
        ids = [e.get("id") for e in root.iter() if e.get("id")]
        assert len(ids) == 4 and len(set(ids)) == 4
        assert all(i.startswith(("p1-", "p2-")) for i in ids)
        refs = re.findall(r"url\(#([^)]+)\)", result.svg_text)
        assert refs and set(refs) <= set(ids)

    def test_inner_title_hidden_by_default_and_shown_on_request(self):
        wrapper = Wrapper("F-16C_50")
        devices = {
            GUID_A: export_device(bound_device(VKB, GUID_A, "A"), VKB, wrapper),
            GUID_B: export_device(bound_device(STARTER, GUID_B, "B"), STARTER, wrapper),
        }
        hidden = compose_page(two_member_page(), wrapper, devices, None)
        # the <title> element and the visible heading: nothing inside the panels
        assert hidden.svg_text.count("F-16C_50") == 2
        shown_page = two_member_page()
        for placement in shown_page.placements:
            placement.hide_inner_title = False
        shown = compose_page(shown_page, wrapper, devices, None)
        assert shown.svg_text.count("F-16C_50") > 2

    def test_legibility_warning_below_six_points(self):
        small, _ = _compose_pair(VKB, WARTHOG, None, size_preset=SizePreset.KNEEBOARD)
        assert small.min_font_pt < 6
        assert any("prints at" in w and "pt" in w for w in small.warnings)
        big, _ = _compose_pair(
            VKB, WARTHOG, None, size_preset=SizePreset.FIT, scale=2.0
        )
        assert big.min_font_pt > 6
        assert not any("prints at" in w for w in big.warnings)


# ── Empty members and the rule ──


class TestEmptyMembersAndRule:
    def _devices(self):
        f16 = Wrapper("F-16C_50")
        a10 = Wrapper("A-10C_2")
        hornet = Wrapper("FA-18C")
        return (
            [
                export_device(bound_device(VKB, GUID_A, "VKB"), VKB, f16),
                export_device(bound_device(WARTHOG, GUID_B, "Throttle"), WARTHOG, f16),
                export_device(bound_device(VKB, GUID_A, "VKB"), VKB, a10),
                export_device(empty_device(GUID_B, "Throttle"), WARTHOG, a10),
                export_device(empty_device(GUID_A, "VKB"), VKB, hornet),
                export_device(bound_device(STARTER, GUID_C, "Other"), STARTER, hornet),
            ],
            (f16, a10, hornet),
        )

    def test_device_has_bindings(self):
        assert not device_has_bindings(empty_device(GUID_A, "x"))
        assert not device_has_bindings(None)
        shell = empty_device(GUID_A, "x")
        shell.create_input(Button(1), "")
        assert not device_has_bindings(shell)
        shell.add_modifier_to_input(Button(2), {"LShift"}, "mod")
        assert device_has_bindings(shell)

    def test_shared_rule_is_the_default_every_controller_bound(self):
        devices, (f16, a10, hornet) = self._devices()
        page = two_member_page()
        assert page.profile_rule is ProfileRule.SHARED
        assert [w.profile_name for w in profiles_for_page(page, devices)] == [
            "F-16C_50"
        ]  # A-10C has no throttle bindings; Hornet has neither

    def test_any_rule_renders_for_every_profile_with_one_bound_controller(self):
        devices, (f16, a10, hornet) = self._devices()
        page = two_member_page(profile_rule=ProfileRule.ANY)
        assert [w.profile_name for w in profiles_for_page(page, devices)] == [
            "F-16C_50",
            "A-10C_2",
        ]  # Hornet has only empty controllers on this page → no file
        plan = page_profile_plan(page, devices)
        assert [(e.wrapper.profile_name, e.missing) for e in plan] == [
            ("F-16C_50", ()),
            ("A-10C_2", (GUID_B,)),
        ]
        # the rule can be asked for without changing the page
        assert len(profiles_for_page(page, devices, ProfileRule.SHARED)) == 1

    def test_member_lookup_prefers_this_profile_then_any_template(self):
        devices, (f16, a10, hornet) = self._devices()
        page = two_member_page()
        for_hornet = member_devices_for_profile(page, hornet, devices)
        assert for_hornet[GUID_A].profile_wrapper is hornet
        assert for_hornet[GUID_B].template is not None  # borrowed from another profile

    def test_empty_member_is_dimmed_with_caption(self):
        devices, (f16, a10, _) = self._devices()
        page = two_member_page()
        result = compose_page(
            page, a10, member_devices_for_profile(page, a10, devices), None
        )
        assert result.empty_members == (GUID_B,)
        assert result.rendered_members == (GUID_A,)
        root = parse(result.svg_text)
        groups = {
            g.get("data-jd-member"): g
            for g in root.findall(f"{{{SVG_NS}}}g")
            if g.get("data-jd-member")
        }
        assert groups[GUID_B].get("opacity") == "0.45"
        assert groups[GUID_A].get("opacity") is None
        captions = [
            t.text
            for t in root.iter(f"{{{SVG_NS}}}text")
            if t.text and t.text.startswith("No bindings")
        ]
        assert captions == ["No bindings in A-10C_2"]
        # the empty panel is still a full template render (boxes, no bindings)
        panels = root.findall(f".//{{{SVG_NS}}}svg")
        assert len(panels) == 2
        assert "cmd button" in etree.tostring(panels[0], encoding="unicode")
        assert "cmd button" not in etree.tostring(panels[1], encoding="unicode")
        # the layout is identical to the fully bound profile's
        bound = compose_page(
            page, f16, member_devices_for_profile(page, f16, devices), None
        )
        assert [p.box for p in bound.panels] == [p.box for p in result.panels]

    def test_control_characters_from_the_original_engine_still_compose(self):
        """The legacy engine turns "\\f" in an action into a form feed (the
        Edge-Cases sample profile); the page must still parse and export."""
        from joystick_diagrams.export import render_template
        from joystick_diagrams.render.context import RenderOutcome

        devices, (f16, _, _) = self._devices()
        page = two_member_page()

        def renderer(export_device, ctx):
            outcome = render_template(export_device, ctx)
            text = outcome.svg_text.replace("cmd button", "cmd\x0cbutton", 1)
            return RenderOutcome(text, outcome.report)

        result = compose_page(
            page,
            f16,
            member_devices_for_profile(page, f16, devices),
            None,
            renderer=renderer,
        )
        assert "\x0c" not in result.svg_text
        assert parse(result.svg_text) is not None

    def test_all_empty_warns(self):
        devices, (_, _, hornet) = self._devices()
        page = two_member_page()
        result = compose_page(
            page, hornet, member_devices_for_profile(page, hornet, devices), None
        )
        assert result.empty_members == (GUID_A, GUID_B)
        assert any("has bindings in FA-18C" in w for w in result.warnings)

    def test_missing_member_or_template_raises(self):
        wrapper = Wrapper("F-16C_50")
        only_a = {GUID_A: export_device(bound_device(VKB, GUID_A, "VKB"), VKB, wrapper)}
        with pytest.raises(ComposeError, match="not in your bindings"):
            compose_page(two_member_page(), wrapper, only_a, None)
        no_template = {
            **only_a,
            GUID_B: export_device(
                bound_device(WARTHOG, GUID_B, "Throttle"), None, wrapper
            ),
        }
        with pytest.raises(ComposeError, match="Throttle needs a template"):
            compose_page(two_member_page(), wrapper, no_template, None)
        with pytest.raises(ComposeError, match="no controllers"):
            compose_page(Page(name="Empty"), wrapper, {}, None)
