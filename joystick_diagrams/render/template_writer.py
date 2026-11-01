"""Bake layout changes into a new, shareable template (plan §5.7 "Save as new template").

``bake_template`` runs the DOM pipeline with **binding fill disabled**: a
``TokenKeepingResolver`` answers every placeholder with itself, so
``BUTTON_1``, ``TEMPLATE_NAME`` and ``CURRENT_DATE`` stay in the output exactly
as written, and only the ``layout`` stage changes anything. Moved and resized
slots get their new geometry (rendered SVG and draw.io ``mxGeometry``), hidden
slots become invisible, and added modifier boxes become real
``<KEY>_MODIFIER_<n>`` placeholders in both the rendered SVG and the embedded
draw.io model, so the file works as an ordinary template in old and new
versions of the app and reopens in draw.io.

Dynamic "one box per modifier" ops have no fixed count; pass ``device`` (the
"Preview with" profile's device) and they are baked for that profile's
modifier counts. Optionally the current style is stored as the template's
look in a ``jd_theme`` root attribute (JSON; plan §3.4 author defaults), which
``resolve_theme(theme, author=...)`` is the hook for. Nothing reads it yet.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from joystick_diagrams.render.auto_layout import counts_from_device
from joystick_diagrams.render.context import RenderContext, RenderFallbackError
from joystick_diagrams.render.layout import LayoutLayers
from joystick_diagrams.render.layout_apply import LayoutNotice, apply_layout
from joystick_diagrams.render.pipeline import (
    DEFAULT_STAGES,
    PipelineHooks,
    RenderJob,
    run_pipeline,
    stage_serialise,
)

JD_THEME_ATTRIBUTE = "jd_theme"
UNLIMITED_BOXES = 99


class TokenKeepingResolver:
    """A resolver that leaves every placeholder in place (case preserved)."""

    def __init__(self, device: Any = None) -> None:
        self._counts: dict[str, int] = (
            counts_from_device(device, UNLIMITED_BOXES) if device is not None else {}
        )

    def text_for(self, token: str) -> str:
        return token

    def html_for(self, token: str) -> str:
        return html.escape(token, quote=False)

    def rich_for(self, token: str, overflow: int = 0):
        return None

    def input_keys(self) -> list[str]:
        return []

    def modifier_count(self, input_key: str) -> int:
        return self._counts.get(input_key.lower(), 0)

    def modifier_for(self, input_key: str, index: int):
        return None

    def modifier_box_colour(self, modifier):
        return None

    def resolve_label(self, command: str) -> str:
        return command


class TemplateBakeError(Exception):
    """The template can't be baked (not draw.io, invalid XML…)."""


@dataclass(frozen=True)
class BakeResult:
    svg_text: str
    skipped_ops: tuple[str, ...] = ()
    notices: tuple[LayoutNotice, ...] = ()
    added_boxes: int = 0
    theme_stored: bool = False
    unplaced: tuple[Any, ...] = field(default_factory=tuple)


def _store_theme_stage(theme: Any):
    def stage(job: RenderJob) -> None:
        assert job.doc is not None
        job.doc.root.set(JD_THEME_ATTRIBUTE, theme.model_dump_json(exclude_none=True))

    return stage


def _strip_annotations(job: RenderJob) -> None:
    """Remove the editor's ``data-jd-*`` attributes: a template should be clean."""
    assert job.doc is not None
    for node in job.doc.root.iter():
        if not isinstance(node.tag, str):
            continue
        for name in [a for a in node.attrib if a.startswith("data-jd-")]:
            del node.attrib[name]


def bake_template(
    template: Any,
    layers: LayoutLayers,
    *,
    device: Any = None,
    theme: Any = None,
    store_theme: bool = False,
) -> BakeResult:
    """Render ``template`` with ``layers`` applied and every token kept.

    ``template`` needs ``raw_data`` (and ideally ``template_key``/``content_hash``
    for drift notices). Raises ``TemplateBakeError`` when the file isn't a
    draw.io SVG the DOM engine can handle.
    """
    ctx = RenderContext(engine_override="dom", preview=False)
    job = RenderJob(
        raw=template.raw_data,
        ctx=ctx,
        resolver=TokenKeepingResolver(device),
        hooks=PipelineHooks(layout=(apply_layout,)),
        template_key=getattr(template, "template_key", None),
        profile_key=None,
        content_hash=_safe_hash(template),
        layers=layers,
        describe_layout=True,
    )
    stages = list(DEFAULT_STAGES)
    stages.insert(stages.index(stage_serialise), _strip_annotations)
    theme_stored = False
    if store_theme and theme is not None:
        stages.insert(stages.index(stage_serialise), _store_theme_stage(theme))
        theme_stored = True
    try:
        outcome = run_pipeline(job, stages)
    except RenderFallbackError as error:
        raise TemplateBakeError(error.detail or error.notice.value) from error
    layout = job.layout
    return BakeResult(
        svg_text=outcome.svg_text,
        skipped_ops=tuple(job.skipped_ops),
        notices=tuple(layout.notices) if layout is not None else (),
        added_boxes=layout.added_count if layout is not None else 0,
        theme_stored=theme_stored,
        unplaced=tuple(layout.unplaced) if layout is not None else (),
    )


def _safe_hash(template: Any) -> str | None:
    try:
        return getattr(template, "content_hash", None)
    except OSError:
        return None


def safe_template_filename(name: str) -> str:
    """A file name for ``name``: forbidden characters replaced, ``.svg`` ensured."""
    cleaned = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in name)
    cleaned = cleaned.strip().strip(".") or "template"
    return cleaned if cleaned.lower().endswith(".svg") else f"{cleaned}.svg"


def write_template(svg_text: str, folder: Path, name: str) -> Path:
    """Write ``svg_text`` as ``folder/<safe name>.svg`` and return the path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_template_filename(name)
    path.write_text(svg_text, encoding="utf-8")
    return path


__all__ = [
    "JD_THEME_ATTRIBUTE",
    "BakeResult",
    "TemplateBakeError",
    "TokenKeepingResolver",
    "bake_template",
    "safe_template_filename",
    "write_template",
]

if __name__ == "__main__":
    pass
