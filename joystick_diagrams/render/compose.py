"""Compose several controllers' diagrams onto one page SVG (``compose_page``).

For one profile, every member of a ``Page`` is rendered through the existing
pipeline (``export.render_template``: DOM engine or legacy, layout ops, style).
Each rendered SVG is then:

1. parsed with the hardened parser, its draw.io ``content`` attribute dropped
   (a page is plain SVG; reopening it in draw.io is not a goal) and the
   "Text is not SVG" footer removed;
2. given a per-panel id prefix (``p1-``, ``p2-`` …) on every ``id`` and every
   reference to one (``url(#…)`` in any attribute, ``href``/``xlink:href="#…"``
   and ``#id`` selectors inside ``<style>``), so two copies of the same template
   cannot collide;
3. nested as ``<svg x y width height viewBox>`` inside the page root, which
   keeps the template's own coordinate system and clipping and scales its
   ``foreignObject`` labels with it.

The page root is sized in **mm** (``viewBox`` in mm too, so user units are mm),
with a title "<profile> · <page name>" and the date, so printed sizes are exact
and the PNG/PDF converter (``export_image``) can size the output.

The rule (``profiles_for_page``, ``Page.profile_rule``): by default
(``ProfileRule.SHARED``) a page renders only for profiles in which every
controller on it has bindings. With ``ProfileRule.ANY`` it renders for every
profile in which at least one has; a controller without bindings in that
profile is drawn from its template with empty boxes, dimmed, with the caption
"No bindings in <profile>", so a laminated layout never shifts.
``page_profile_plan`` lists the profiles with the controllers missing in each.

Legibility: the smallest font size found in any panel, times that panel's
scale, is the smallest printed point size; below ``MIN_LEGIBLE_PT`` a warning is
added.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from lxml import etree

from joystick_diagrams.input.device import Device_
from joystick_diagrams.render.context import RenderContext, RenderOutcome, RenderReport
from joystick_diagrams.render.document import make_parser
from joystick_diagrams.render.page import (
    CAPTION_FONT_MM,
    DATE_FONT_MM,
    MIN_LEGIBLE_PT,
    TITLE_FONT_MM,
    Page,
    PageLayout,
    PanelBox,
    ProfileRule,
    layout_page,
    printed_pt,
)

_logger = logging.getLogger(__name__)

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
_SVG = f"{{{SVG_NS}}}"
_XLINK_HREF = f"{{{XLINK_NS}}}href"

DIMMED_OPACITY = "0.45"
PANEL_FONT_FAMILY = "Helvetica, Arial, sans-serif"

_URL_REF_RE = re.compile(r"url\(\s*(['\"]?)#([^'\")\s]+)\1\s*\)")
_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([\d.]+)\s*(px|pt)?", re.IGNORECASE)
_NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


class ComposeError(Exception):
    """A page cannot be composed (a member has no template, or no members)."""


@dataclass(frozen=True)
class PanelRender:
    device_guid: str
    device_name: str
    box: PanelBox
    empty: bool  # no bindings in this profile → dimmed with a caption
    report: RenderReport | None
    min_font_px: float | None


@dataclass(frozen=True)
class ComposeResult:
    svg_text: str
    warnings: tuple[str, ...]
    rendered_members: tuple[str, ...]  # device guids drawn with bindings
    empty_members: tuple[str, ...]  # device guids drawn empty and dimmed
    min_font_pt: float | None
    width_mm: float
    height_mm: float
    panels: tuple[PanelRender, ...] = field(default_factory=tuple)


Renderer = Callable[[Any, RenderContext | None], RenderOutcome]


# ── The rule: which profiles a page renders for ──


def device_has_bindings(device: Any) -> bool:
    """True when any control on the device has a command or a modifier."""
    if device is None:
        return False
    for input_object in device.get_combined_inputs().values():
        if (input_object.command or "").strip() or input_object.modifiers:
            return True
    return False


@dataclass(frozen=True)
class PageProfile:
    """One profile a page would be made for, and the controllers on the page
    that have no bindings in it (drawn empty under ``ProfileRule.ANY``)."""

    wrapper: Any
    missing: tuple[str, ...] = ()


def page_profile_plan(
    page: Page, export_devices: Iterable[Any], rule: ProfileRule | None = None
) -> list[PageProfile]:
    """The profiles (by first appearance) ``page`` is made for under ``rule``
    (the page's own rule when ``None``), each with its missing controllers."""
    rule = ProfileRule(rule or page.profile_rule)
    members = page.member_guids
    wanted = set(members)
    order: dict[str, Any] = {}
    bound: dict[str, set[str]] = {}
    for export_device in export_devices:
        guid = export_device.device_id
        if guid not in wanted:
            continue
        wrapper = export_device.profile_wrapper
        key = _profile_key(wrapper)
        order.setdefault(key, wrapper)
        if device_has_bindings(export_device.device):
            bound.setdefault(key, set()).add(guid)
    plan: list[PageProfile] = []
    for key, wrapper in order.items():
        have = bound.get(key, set())
        if not have:
            continue
        missing = tuple(g for g in members if g not in have)
        if rule is ProfileRule.SHARED and missing:
            continue
        plan.append(PageProfile(wrapper, missing))
    return plan


def profiles_for_page(
    page: Page, export_devices: Iterable[Any], rule: ProfileRule | None = None
) -> list[Any]:
    """The profile wrappers a page is made for: by default (``ProfileRule.SHARED``)
    those in which every controller on it has bindings; under ``ANY`` those in
    which at least one has."""
    return [entry.wrapper for entry in page_profile_plan(page, export_devices, rule)]


def member_devices_for_profile(
    page: Page, profile_wrapper: Any, export_devices: Iterable[Any]
) -> dict[str, Any]:
    """``{device_guid: ExportDevice}`` for ``compose_page``: this profile's member
    when it exists, else any profile's copy that carries the template."""
    members = set(page.member_guids)
    wanted = _profile_key(profile_wrapper)
    chosen: dict[str, Any] = {}
    for export_device in export_devices:
        guid = export_device.device_id
        if guid not in members:
            continue
        current = chosen.get(guid)
        is_this_profile = _profile_key(export_device.profile_wrapper) == wanted
        if current is None:
            chosen[guid] = export_device
        elif is_this_profile and _profile_key(current.profile_wrapper) != wanted:
            chosen[guid] = export_device
        elif current.template is None and export_device.template is not None:
            chosen[guid] = export_device
    return chosen


def _profile_key(wrapper: Any) -> str:
    return str(
        getattr(wrapper, "profile_key", None) or getattr(wrapper, "profile_name", "")
    )


# ── Panel preparation ──


class _PanelWrapper:
    """A profile wrapper proxy with a blank name, so the member's own
    TEMPLATE_NAME box stays empty (the page carries the shared title)."""

    def __init__(self, wrapper: Any, blank_name: bool) -> None:
        self._wrapper = wrapper
        self._blank_name = blank_name

    @property
    def profile_name(self) -> str:
        return "" if self._blank_name else self._wrapper.profile_name

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapper, name)


def _empty_copy(export_device: Any, profile_wrapper: Any) -> Any:
    """An ExportDevice-like object with the same template and no bindings."""
    from joystick_diagrams.export_device import ExportDevice

    device = export_device.device
    empty = Device_(device.guid, device.name)
    copy = ExportDevice(empty, None, profile_wrapper)
    copy._template = export_device.template  # skip the compatibility check
    return copy


def _with_wrapper(export_device: Any, wrapper: Any) -> Any:
    from joystick_diagrams.export_device import ExportDevice

    copy = ExportDevice(export_device.device, None, wrapper)
    copy._template = export_device.template
    return copy


def _default_renderer() -> Renderer:
    from joystick_diagrams.export import render_template

    return render_template


def _parse_number(value: str | None, default: float) -> float:
    match = _NUMBER_RE.search(value or "")
    return float(match.group(0)) if match else default


def panel_viewbox(root: etree._Element) -> tuple[float, float, float, float]:
    """The member's viewBox (x, y, w, h); falls back to width/height, then 800×600."""
    view_box = root.get("viewBox")
    if view_box:
        parts = _NUMBER_RE.findall(view_box)
        if len(parts) == 4:
            x, y, w, h = (float(p) for p in parts)
            if w > 0 and h > 0:
                return x, y, w, h
    width = _parse_number(root.get("width"), 800.0)
    height = _parse_number(root.get("height"), 600.0)
    return 0.0, 0.0, width or 800.0, height or 600.0


def strip_drawio_footer(root: etree._Element) -> None:
    """Remove draw.io's trailing ``<switch>`` ("Text is not SVG - cannot display")."""
    for child in list(root):
        if child.tag != f"{_SVG}switch":
            continue
        has_feature_gate = any(
            node.tag == f"{_SVG}g" and node.get("requiredFeatures") is not None
            for node in child
        )
        has_link = any(node.tag == f"{_SVG}a" for node in child)
        if has_feature_gate and has_link:
            root.remove(child)


def _elements(root: etree._Element):
    return (element for element in root.iter() if isinstance(element.tag, str))


def _rename_ids(root: etree._Element, prefix: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for element in _elements(root):
        old = element.get("id")
        if old:
            mapping[old] = f"{prefix}{old}"
            element.set("id", mapping[old])
    return mapping


def _rewrite_attribute_refs(element: etree._Element, mapping: dict[str, str]) -> None:
    def rewrite_url(match: re.Match[str]) -> str:
        quote, ref = match.group(1), match.group(2)
        return f"url({quote}#{mapping.get(ref, ref)}{quote})"

    for name, value in list(element.attrib.items()):
        if name in ("href", _XLINK_HREF) and value.startswith("#"):
            if value[1:] in mapping:
                element.set(name, f"#{mapping[value[1:]]}")
        elif "url(" in value:
            element.set(name, _URL_REF_RE.sub(rewrite_url, value))


def _rewrite_style_refs(style: etree._Element, mapping: dict[str, str]) -> None:
    if not style.text:
        return
    selector_re = re.compile(
        r"#("
        + "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))
        + r")(?![\w-])"
    )
    text = selector_re.sub(lambda m: f"#{mapping[m.group(1)]}", style.text)
    style.text = _URL_REF_RE.sub(
        lambda m: (
            f"url({m.group(1)}#{mapping.get(m.group(2), m.group(2))}{m.group(1)})"
        ),
        text,
    )


def prefix_ids(root: etree._Element, prefix: str) -> dict[str, str]:
    """Prefix every id under ``root`` and rewrite every reference to one:
    ``url(#id)`` in any attribute, ``href``/``xlink:href="#id"`` and ``#id``
    selectors or ``url(#id)`` inside ``<style>``. Returns ``{old: new}``."""
    mapping = _rename_ids(root, prefix)
    if not mapping:
        return mapping
    for element in _elements(root):
        _rewrite_attribute_refs(element, mapping)
        if element.tag == f"{_SVG}style":
            _rewrite_style_refs(element, mapping)
    return mapping


def smallest_font_px(root: etree._Element) -> float | None:
    """The smallest positive font size (px) declared on any element under ``root``."""
    smallest: float | None = None
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        candidates: list[float] = []
        attr = element.get("font-size")
        if attr:
            number = _parse_number(attr, 0.0)
            if attr.strip().endswith("pt"):
                number *= 96.0 / 72.0
            candidates.append(number)
        style = element.get("style")
        if style and "font-size" in style:
            for value, unit in _FONT_SIZE_RE.findall(style):
                number = float(value)
                if unit.lower() == "pt":
                    number *= 96.0 / 72.0
                candidates.append(number)
        for number in candidates:
            if number > 0 and (smallest is None or number < smallest):
                smallest = number
    return smallest


@dataclass
class _PreparedPanel:
    guid: str
    name: str
    root: etree._Element
    view_box: tuple[float, float, float, float]
    empty: bool
    report: RenderReport | None
    min_font_px: float | None
    hide_inner_title: bool


@dataclass(frozen=True)
class _ComposeRun:
    """What every panel of one ``compose_page`` call shares."""

    profile_wrapper: Any
    ctx: RenderContext | None
    renderer: Renderer

    @property
    def profile_name(self) -> str:
        return str(getattr(self.profile_wrapper, "profile_name", "") or "")


_XML_INVALID_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _render_member(
    run: _ComposeRun, index: int, placement: Any, export_device: Any
) -> _PreparedPanel:
    device = export_device.device
    is_this_profile = _profile_key(export_device.profile_wrapper) == _profile_key(
        run.profile_wrapper
    )
    empty = not (is_this_profile and device_has_bindings(device))
    wrapper = _PanelWrapper(run.profile_wrapper, placement.hide_inner_title)
    target = (
        _empty_copy(export_device, wrapper)
        if empty
        else _with_wrapper(export_device, wrapper)
    )
    outcome = run.renderer(target, run.ctx)
    # The original (legacy) engine can leave XML-invalid control characters in a
    # standalone diagram (a "\f" in an action name); a page must still parse.
    svg_text = _XML_INVALID_CHARS.sub("", outcome.svg_text)
    root = etree.fromstring(svg_text.encode("utf-8"), make_parser())
    if root.tag != f"{_SVG}svg":
        raise ComposeError(f"{device.name}: the rendered diagram is not an SVG")
    view_box = panel_viewbox(root)
    root.attrib.pop("content", None)
    strip_drawio_footer(root)
    prefix_ids(root, f"p{index}-")
    return _PreparedPanel(
        guid=device.guid,
        name=device.name,
        root=root,
        view_box=view_box,
        empty=empty,
        report=outcome.report,
        min_font_px=smallest_font_px(root),
        hide_inner_title=placement.hide_inner_title,
    )


# ── Page assembly ──


def _fmt(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


@dataclass(frozen=True)
class _TextSpec:
    size_mm: float
    anchor: str = "start"
    weight: str | None = None
    fill: str = "#000000"


_TITLE_TEXT = _TextSpec(TITLE_FONT_MM, weight="bold")
_DATE_TEXT = _TextSpec(DATE_FONT_MM, anchor="end", fill="#444444")
_CAPTION_TEXT = _TextSpec(CAPTION_FONT_MM, anchor="middle", fill="#333333")


def _text(
    parent: etree._Element, text: str, x: float, y: float, spec: _TextSpec
) -> etree._Element:
    node = etree.SubElement(parent, f"{_SVG}text", x=_fmt(x), y=_fmt(y), fill=spec.fill)
    node.set("font-family", PANEL_FONT_FAMILY)
    node.set("font-size", _fmt(spec.size_mm))
    node.set("text-anchor", spec.anchor)
    if spec.weight:
        node.set("font-weight", spec.weight)
    node.text = text
    return node


def _nest_panel(parent: etree._Element, panel: _PreparedPanel, box: PanelBox) -> None:
    x, y, w, h = panel.view_box
    nested = etree.SubElement(
        parent,
        f"{_SVG}svg",
        x=_fmt(box.x_mm),
        y=_fmt(box.y_mm),
        width=_fmt(box.width_mm),
        height=_fmt(box.height_mm),
        viewBox=f"{_fmt(x)} {_fmt(y)} {_fmt(w)} {_fmt(h)}",
        preserveAspectRatio="xMidYMid meet",
    )
    nested.set("data-jd-panel", panel.guid)
    style = panel.root.get("style")
    if style:
        nested.set("style", style)
    for child in list(panel.root):
        nested.append(child)


def _date_text(ctx: RenderContext | None) -> str:
    from joystick_diagrams.export import export_date_format

    now = (ctx.now if ctx is not None else None) or datetime.now()
    return now.strftime(export_date_format())


def _assemble(
    page: Page,
    profile_name: str,
    panels: list[_PreparedPanel],
    layout: PageLayout,
    ctx: RenderContext | None,
) -> str:
    root = etree.Element(
        f"{_SVG}svg",
        nsmap={None: SVG_NS, "xlink": XLINK_NS},
    )
    root.set("version", "1.1")
    root.set("width", f"{_fmt(layout.width_mm)}mm")
    root.set("height", f"{_fmt(layout.height_mm)}mm")
    root.set("viewBox", f"0 0 {_fmt(layout.width_mm)} {_fmt(layout.height_mm)}")
    root.set("data-jd-page", page.page_id)
    title = page.title_for(profile_name)
    etree.SubElement(root, f"{_SVG}title").text = title
    etree.SubElement(
        root,
        f"{_SVG}rect",
        x="0",
        y="0",
        width=_fmt(layout.width_mm),
        height=_fmt(layout.height_mm),
        fill="#ffffff",
    )
    if layout.title_y_mm is not None:
        if page.show_title:
            _text(root, title, page.margin_mm, layout.title_y_mm, _TITLE_TEXT)
        if page.show_date:
            _text(
                root,
                _date_text(ctx),
                layout.width_mm - page.margin_mm,
                layout.title_y_mm,
                _DATE_TEXT,
            )
    for panel, box in zip(panels, layout.panels, strict=True):
        group = etree.SubElement(root, f"{_SVG}g")
        group.set("data-jd-member", panel.guid)
        if panel.empty:
            group.set("opacity", DIMMED_OPACITY)
        _nest_panel(group, panel, box)
        if panel.empty:
            caption = etree.SubElement(root, f"{_SVG}g")
            caption.set("data-jd-caption", panel.guid)
            _text(
                caption,
                f"No bindings in {profile_name}",
                box.x_mm + box.width_mm / 2,
                box.y_mm + CAPTION_FONT_MM * 1.5,
                _CAPTION_TEXT,
            )
    for note in page.notes:
        _text(root, note.text, note.x_mm, note.y_mm, _TextSpec(note.font_mm))
    body = etree.tostring(root, encoding="unicode", with_tail=False)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'


def compose_page(
    page: Page,
    profile_wrapper: Any,
    export_devices_by_guid: Mapping[str, Any],
    ctx: RenderContext | None = None,
    *,
    renderer: Renderer | None = None,
) -> ComposeResult:
    """Render ``page`` for one profile.

    ``export_devices_by_guid`` maps every member guid to an ``ExportDevice`` that
    carries the member's template. When that ExportDevice belongs to another
    profile (``profile_key`` differs) or its device has no bindings, the member
    is drawn empty and dimmed. Raises ``ComposeError`` when a member is missing
    from the mapping or has no template.
    """
    if not page.placements:
        raise ComposeError("The page has no controllers on it.")
    run = _ComposeRun(
        profile_wrapper, ctx, renderer if renderer is not None else _default_renderer()
    )
    profile_name = run.profile_name

    prepared: list[_PreparedPanel] = []
    for index, placement in enumerate(page.placements, 1):
        export_device = export_devices_by_guid.get(placement.device_guid)
        if export_device is None:
            raise ComposeError(
                f"A controller on this page is not in your bindings: {placement.device_guid}"
            )
        if export_device.template is None:
            raise ComposeError(f"{export_device.device.name} needs a template")
        prepared.append(_render_member(run, index, placement, export_device))

    layout = layout_page(page, [(p.view_box[2], p.view_box[3]) for p in prepared])
    svg_text = _assemble(page, profile_name, prepared, layout, ctx)

    warnings: list[str] = []
    min_pt: float | None = None
    panel_renders: list[PanelRender] = []
    for panel, box in zip(prepared, layout.panels, strict=True):
        pt = printed_pt(panel.min_font_px, box.mm_per_px) if panel.min_font_px else None
        if pt is not None:
            min_pt = pt if min_pt is None else min(min_pt, pt)
            if pt < MIN_LEGIBLE_PT:
                warnings.append(
                    f"Text on {panel.name} prints at {pt:.1f} pt. "
                    "Make it larger for readability."
                )
        if (
            box.x_mm < 0
            or box.y_mm < 0
            or box.x_mm + box.width_mm > layout.width_mm + 1e-6
            or box.y_mm + box.height_mm > layout.height_mm + 1e-6
        ):
            warnings.append(f"{panel.name} does not fit on the page.")
        panel_renders.append(
            PanelRender(
                panel.guid,
                panel.name,
                box,
                panel.empty,
                panel.report,
                panel.min_font_px,
            )
        )
    if all(panel.empty for panel in prepared):
        warnings.append(f"No controller on this page has bindings in {profile_name}.")

    return ComposeResult(
        svg_text=svg_text,
        warnings=tuple(warnings),
        rendered_members=tuple(p.guid for p in prepared if not p.empty),
        empty_members=tuple(p.guid for p in prepared if p.empty),
        min_font_pt=min_pt,
        width_mm=layout.width_mm,
        height_mm=layout.height_mm,
        panels=tuple(panel_renders),
    )


__all__ = [
    "ComposeError",
    "ComposeResult",
    "PanelRender",
    "compose_page",
    "device_has_bindings",
    "member_devices_for_profile",
    "prefix_ids",
    "profiles_for_page",
    "smallest_font_px",
    "strip_drawio_footer",
]

if __name__ == "__main__":
    pass
