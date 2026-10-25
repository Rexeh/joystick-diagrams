"""Page model and layout maths for combined pages (several controllers on one sheet).

Pure data (pydantic v2) plus the preset layout arithmetic. No rendering here:
``render/compose.py`` turns a ``Page`` plus rendered member diagrams into one
SVG; ``db/page_service.py`` persists pages.

A page lists its members as ``Placement`` rows keyed by ``device_guid`` (never by
template), so a page follows its controller when the template changes. v1 only
places members with a preset (``Arrangement``) and a uniform scale; the
``x_mm``/``y_mm``/``scale`` fields on a placement are honoured when set so that
free placement (v2) needs no schema change.

Units: page geometry is in millimetres; member diagrams are in CSS px
(their ``viewBox``). ``MM_PER_PX`` converts at 96 dpi, which is what browsers
and the PNG converter assume.

JSON shape (``Page.model_dump_json()``)::

    {
        "schema_version": 1,
        "page_id": "page_…",
        "name": "Stick + Throttle",
        "size_preset": "a4",
        "width_mm": null,
        "height_mm": null,
        "orientation": "auto",
        "arrangement": "side_by_side",
        "placements": [
            {
                "device_guid": "…",
                "x_mm": null,
                "y_mm": null,
                "scale": 1.0,
                "hide_inner_title": true,
            }
        ],
        "gap_mm": 6.0,
        "margin_mm": 10.0,
        "scale": 1.0,
        "title": null,
        "show_title": true,
        "show_date": true,
        "notes": [],
        "export_members_separately": false,
    }
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1

MM_PER_PX = 25.4 / 96.0  # CSS reference pixel at 96 dpi
MM_PER_PT = 25.4 / 72.0
MIN_LEGIBLE_PT = 6.0  # warn when printed text would be smaller than this
TITLE_BAND_MM = 12.0  # height reserved above the panels for title and date
CAPTION_FONT_MM = 3.5  # "No bindings in …" caption (≈10 pt)
TITLE_FONT_MM = 5.0  # page title (≈14 pt)
DATE_FONT_MM = 3.5

MIN_MEMBERS = 2


class SizePreset(str, Enum):
    A4 = "a4"
    LETTER = "letter"
    KNEEBOARD = "kneeboard"  # 5.5 × 8.5 in
    FIT = "fit"  # page grows to the content
    CUSTOM = "custom"  # width_mm / height_mm


# Portrait dimensions (width, height) in mm.
PAGE_SIZES_MM: dict[SizePreset, tuple[float, float]] = {
    SizePreset.A4: (210.0, 297.0),
    SizePreset.LETTER: (215.9, 279.4),
    SizePreset.KNEEBOARD: (139.7, 215.9),
}

# User-facing names (glossary: "page size"); the UI may show these directly.
SIZE_PRESET_LABELS: dict[SizePreset, str] = {
    SizePreset.A4: "A4",
    SizePreset.LETTER: "Letter",
    SizePreset.KNEEBOARD: "Kneeboard 5.5 × 8.5 in",
    SizePreset.FIT: "Fit to content",
    SizePreset.CUSTOM: "Custom",
}


class Orientation(str, Enum):
    AUTO = "auto"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class Arrangement(str, Enum):
    SIDE_BY_SIDE = "side_by_side"
    STACKED = "stacked"
    GRID = "grid"


ARRANGEMENT_LABELS: dict[Arrangement, str] = {
    Arrangement.SIDE_BY_SIDE: "Side by side",
    Arrangement.STACKED: "Stacked",
    Arrangement.GRID: "Grid",
}


class Placement(BaseModel):
    device_guid: str
    x_mm: float | None = None  # None → placed by the arrangement preset
    y_mm: float | None = None
    scale: float = 1.0  # relative to the preset's uniform scale
    hide_inner_title: bool = True  # the member's own TEMPLATE_NAME is blanked


class PageNote(BaseModel):
    text: str
    x_mm: float
    y_mm: float
    font_mm: float = 3.5


def new_page_id() -> str:
    return f"page_{uuid.uuid4().hex}"


class ProfileRule(str, Enum):
    """Which profiles a page is made for.

    ``SHARED`` (the default): only profiles in which every controller on the page
    has bindings. ``ANY``: every profile in which at least one of them has
    bindings; a controller without bindings there is drawn dimmed with the
    caption "No bindings in <profile>".
    """

    SHARED = "shared"
    ANY = "any"


class Page(BaseModel):
    schema_version: int = SCHEMA_VERSION
    page_id: str = Field(default_factory=new_page_id)
    name: str
    size_preset: SizePreset = SizePreset.A4
    width_mm: float | None = None  # CUSTOM only
    height_mm: float | None = None
    orientation: Orientation = Orientation.AUTO
    arrangement: Arrangement = Arrangement.SIDE_BY_SIDE
    placements: list[Placement] = Field(default_factory=list)
    gap_mm: float = 6.0
    margin_mm: float = 10.0
    scale: float = 1.0  # the scale slider: 1.0 fills the page, smaller shrinks
    title: str | None = None  # None → "<profile> · <page name>"
    show_title: bool = True
    show_date: bool = True
    notes: list[PageNote] = Field(default_factory=list)
    export_members_separately: bool = False
    profile_rule: ProfileRule = ProfileRule.SHARED
    updated_at: str | None = None

    @property
    def member_guids(self) -> list[str]:
        return [placement.device_guid for placement in self.placements]

    def title_for(self, profile_name: str) -> str:
        return self.title if self.title else f"{profile_name} · {self.name}"


def validate_page(page: Page) -> list[str]:
    """Problems with a page as plain sentences; empty when the page is valid."""
    problems: list[str] = []
    if not " ".join(page.name.split()):
        problems.append("A page needs a name.")
    guids = page.member_guids
    if len(set(guids)) < MIN_MEMBERS:
        problems.append("A page needs at least 2 different controllers.")
    if len(set(guids)) != len(guids):
        problems.append("A controller can only be on a page once.")
    if page.size_preset is SizePreset.CUSTOM and not (
        (page.width_mm or 0) > 0 and (page.height_mm or 0) > 0
    ):
        problems.append("A custom page size needs a width and a height.")
    if not 0.1 <= page.scale <= 4.0:
        problems.append("Scale must be between 10% and 400%.")
    if page.gap_mm < 0 or page.margin_mm < 0:
        problems.append("Gaps and margins cannot be negative.")
    for placement in page.placements:
        if placement.scale <= 0:
            problems.append("A controller's scale must be greater than 0.")
            break
    return problems


# ── Layout maths ──


@dataclass(frozen=True)
class PanelBox:
    """Where one member sits on the page, in mm, with its uniform scale (mm per px)."""

    device_guid: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    mm_per_px: float


@dataclass(frozen=True)
class PageLayout:
    width_mm: float
    height_mm: float
    panels: tuple[PanelBox, ...]
    title_y_mm: float | None  # baseline of the title line, None when hidden
    content_top_mm: float

    @property
    def landscape(self) -> bool:
        return self.width_mm > self.height_mm


def grid_shape(arrangement: Arrangement, count: int) -> tuple[int, int]:
    """(rows, cols) for ``count`` panels."""
    count = max(count, 1)
    if arrangement is Arrangement.SIDE_BY_SIDE:
        return 1, count
    if arrangement is Arrangement.STACKED:
        return count, 1
    cols = math.ceil(math.sqrt(count))
    return math.ceil(count / cols), cols


def _cell_sizes(
    sizes_px: Sequence[tuple[float, float]], rows: int, cols: int
) -> tuple[list[float], list[float]]:
    """Column widths and row heights (px) of the grid, from the panels' natural sizes."""
    col_w = [0.0] * cols
    row_h = [0.0] * rows
    for index, (width, height) in enumerate(sizes_px):
        row, col = divmod(index, cols)
        col_w[col] = max(col_w[col], width)
        row_h[row] = max(row_h[row], height)
    return col_w, row_h


def _resolve_orientation(
    page: Page, content_w_px: float, content_h_px: float
) -> Orientation:
    if page.orientation is not Orientation.AUTO:
        return page.orientation
    if page.arrangement is Arrangement.SIDE_BY_SIDE:
        return Orientation.LANDSCAPE
    if page.arrangement is Arrangement.STACKED:
        return Orientation.PORTRAIT
    return (
        Orientation.LANDSCAPE if content_w_px >= content_h_px else Orientation.PORTRAIT
    )


def page_size_mm(
    page: Page, content_w_px: float, content_h_px: float
) -> tuple[float, float]:
    """The sheet size in mm for a preset or custom page (``FIT`` is sized by
    ``layout_page`` from the content, gaps included)."""
    if page.size_preset is SizePreset.FIT:
        raise ValueError("Fit to content has no fixed size")
    if page.size_preset is SizePreset.CUSTOM:
        width, height = float(page.width_mm or 0), float(page.height_mm or 0)
    else:
        width, height = PAGE_SIZES_MM[page.size_preset]
    orientation = _resolve_orientation(page, content_w_px, content_h_px)
    if orientation is Orientation.LANDSCAPE and width < height:
        width, height = height, width
    elif orientation is Orientation.PORTRAIT and width > height:
        width, height = height, width
    return width, height


def layout_page(page: Page, sizes_px: Sequence[tuple[float, float]]) -> PageLayout:
    """Place every member (``sizes_px`` in placement order) on the sheet.

    One uniform ``mm_per_px`` makes the grid of panels fit inside the margins
    (times ``page.scale``), so every panel keeps its aspect ratio and all panels
    share the same text size. The block is centred horizontally and sits under
    the title band. A placement with explicit ``x_mm``/``y_mm`` is placed there
    instead, at ``mm_per_px × placement.scale``.
    """
    count = len(sizes_px)
    rows, cols = grid_shape(page.arrangement, count)
    col_w, row_h = _cell_sizes(sizes_px, rows, cols)
    content_w_px = sum(col_w)
    content_h_px = sum(row_h)
    title_band = TITLE_BAND_MM if page.show_title or page.show_date else 0.0
    gaps_w = page.gap_mm * (cols - 1)
    gaps_h = page.gap_mm * (rows - 1)

    if page.size_preset is SizePreset.FIT:
        width_mm = content_w_px * MM_PER_PX * page.scale + 2 * page.margin_mm + gaps_w
        height_mm = (
            content_h_px * MM_PER_PX * page.scale
            + 2 * page.margin_mm
            + gaps_h
            + title_band
        )
        mm_per_px = MM_PER_PX * page.scale
    else:
        width_mm, height_mm = page_size_mm(page, content_w_px, content_h_px)
        avail_w = max(width_mm - 2 * page.margin_mm - gaps_w, 1.0)
        avail_h = max(height_mm - 2 * page.margin_mm - gaps_h - title_band, 1.0)
        fit = min(
            avail_w / content_w_px if content_w_px else 1.0,
            avail_h / content_h_px if content_h_px else 1.0,
        )
        mm_per_px = fit * page.scale

    block_w = content_w_px * mm_per_px + gaps_w
    block_h = content_h_px * mm_per_px + gaps_h
    content_top = page.margin_mm + title_band
    avail_h_mm = height_mm - content_top - page.margin_mm
    origin_x = (width_mm - block_w) / 2
    origin_y = content_top + max((avail_h_mm - block_h) / 2, 0.0)

    panels: list[PanelBox] = []
    y = origin_y
    for row in range(rows):
        x = origin_x
        for col in range(cols):
            index = row * cols + col
            if index >= count:
                break
            width_px, height_px = sizes_px[index]
            placement = page.placements[index]
            scale = mm_per_px * placement.scale
            cell_w = col_w[col] * mm_per_px
            cell_h = row_h[row] * mm_per_px
            if placement.x_mm is not None and placement.y_mm is not None:
                px, py = placement.x_mm, placement.y_mm
            else:
                # centre the panel inside its grid cell
                px = x + (cell_w - width_px * scale) / 2
                py = y + (cell_h - height_px * scale) / 2
            panels.append(
                PanelBox(
                    placement.device_guid,
                    px,
                    py,
                    width_px * scale,
                    height_px * scale,
                    scale,
                )
            )
            x += cell_w + page.gap_mm
        y += row_h[row] * mm_per_px + page.gap_mm

    title_y = page.margin_mm + TITLE_FONT_MM if title_band else None
    return PageLayout(width_mm, height_mm, tuple(panels), title_y, content_top)


def printed_pt(font_px: float, mm_per_px: float) -> float:
    """The point size a template font of ``font_px`` prints at under ``mm_per_px``."""
    return font_px * mm_per_px / MM_PER_PT


if __name__ == "__main__":
    pass
