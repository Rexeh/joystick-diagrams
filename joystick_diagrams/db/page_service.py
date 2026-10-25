"""Cached, write-through access to combined pages (``render/page.py`` model).

Mirrors ``ThemeService``/``LayoutService``: a dict cache keyed by ``page_id``
loaded once, every write goes to the database and the cache together, invalid
rows are logged and skipped, and ``ValueError`` carries the plain-language
reasons from ``validate_page`` (at least 2 different controllers, a name, …).

How the Pages UI (F3) uses it::

    service = AppState().page_service
    page = service.create(
        "Stick + Throttle",
        [vkb_guid, throttle_guid],
        arrangement=Arrangement.SIDE_BY_SIDE,
        size_preset=SizePreset.A4,
    )
    service.pages()  # list[Page], by name
    service.rename(page.page_id, "Kneeboard")
    service.save(page.model_copy(update={"scale": 0.9}))
    service.duplicate(page.page_id)  # "<name> copy"
    service.remove_member(guid)  # a controller left every page it was on
    service.pages_for_device(guid)  # "(on <page> page)" in Export rows
    service.members_exported_separately()  # guids whose own rows stay ticked
    service.delete(page.page_id)
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from joystick_diagrams.db import db_pages
from joystick_diagrams.render.page import (
    Arrangement,
    Orientation,
    Page,
    PageNote,
    Placement,
    SizePreset,
    validate_page,
)

_logger = logging.getLogger(__name__)

_OPS_FIELDS = (
    "schema_version",
    "gap_mm",
    "margin_mm",
    "scale",
    "title",
    "show_title",
    "show_date",
    "notes",
)


def _page_from_row(row: db_pages.PageRow) -> Page:
    (
        page_id,
        name,
        size_preset,
        width_mm,
        height_mm,
        orientation,
        arrangement,
        placements_json,
        ops_json,
        export_members_separately,
        updated_at,
        profile_rule,
    ) = row
    ops = json.loads(ops_json or "{}")
    data = {
        "page_id": page_id,
        "name": name,
        "size_preset": size_preset,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "orientation": orientation,
        "arrangement": arrangement,
        "placements": json.loads(placements_json or "[]"),
        "export_members_separately": bool(export_members_separately),
        "profile_rule": profile_rule or "shared",
        "updated_at": updated_at,
        **{key: ops[key] for key in _OPS_FIELDS if key in ops},
    }
    return Page.model_validate(data)


def _record(page: Page) -> db_pages.PageRecord:
    dumped = page.model_dump(mode="json")
    ops = {key: dumped[key] for key in _OPS_FIELDS}
    return db_pages.PageRecord(
        page_id=page.page_id,
        name=page.name,
        size_preset=page.size_preset.value,
        width_mm=page.width_mm,
        height_mm=page.height_mm,
        orientation=page.orientation.value,
        arrangement=page.arrangement.value,
        placements_json=json.dumps(dumped["placements"]),
        ops_json=json.dumps(ops),
        export_members_separately=page.export_members_separately,
        profile_rule=page.profile_rule.value,
    )


def copy_name(base_name: str, taken: set[str]) -> str:
    """ "<name> copy", then "<name> copy 2" … until free (case-insensitive)."""
    lowered = {name.casefold() for name in taken}
    candidate = f"{base_name} copy"
    name = candidate
    suffix = 2
    while name.casefold() in lowered:
        name = f"{candidate} {suffix}"
        suffix += 1
    return name


class PageService:
    def __init__(self):
        self._pages: dict[str, Page] = {}
        self._load_cache()

    # ── Loading ────────────────────────────────────────────────────────

    def _load_cache(self) -> None:
        self._pages = {}
        for row in db_pages.get_all_pages():
            try:
                page = _page_from_row(row)
            except (ValidationError, ValueError, TypeError) as err:
                _logger.warning(f"Skipping invalid stored page {row[0]!r}: {err}")
                continue
            self._pages[page.page_id] = page
        _logger.info(f"Loaded {len(self._pages)} pages from database")

    # ── Read API ───────────────────────────────────────────────────────

    def pages(self) -> list[Page]:
        return sorted(self._pages.values(), key=lambda p: p.name.casefold())

    def get(self, page_id: str) -> Page | None:
        return self._pages.get(page_id)

    def pages_for_device(self, device_guid: str) -> list[Page]:
        """Every page the controller is on, by name."""
        return [p for p in self.pages() if device_guid in p.member_guids]

    def member_guids(self) -> set[str]:
        """Every controller that is on at least one page."""
        return {guid for page in self._pages.values() for guid in page.member_guids}

    def members_exported_separately(self) -> set[str]:
        """Controllers on a page whose own diagram is still exported."""
        return {
            guid
            for page in self._pages.values()
            if page.export_members_separately
            for guid in page.member_guids
        }

    def name_taken(self, name: str, except_page_id: str | None = None) -> bool:
        wanted = " ".join(name.split()).casefold()
        return any(
            p.name.casefold() == wanted
            for p in self._pages.values()
            if p.page_id != except_page_id
        )

    # ── Write API ──────────────────────────────────────────────────────

    def validate(self, page: Page) -> list[str]:
        problems = validate_page(page)
        if self.name_taken(page.name, except_page_id=page.page_id):
            problems.append(f"A page named {page.name.strip()!r} already exists.")
        return problems

    def save(self, page: Page) -> Page:
        """Create or update a page. Raises ``ValueError`` listing every problem."""
        page = page.model_copy(update={"name": " ".join(page.name.split())})
        problems = self.validate(page)
        if problems:
            raise ValueError(" ".join(problems))
        updated_at = db_pages.upsert_page(_record(page))
        stored = page.model_copy(update={"updated_at": updated_at})
        self._pages[stored.page_id] = stored
        return stored

    def create(self, name: str, member_guids: list[str], **fields) -> Page:
        """A new page with the given controllers placed by the arrangement preset.

        ``fields`` are any other ``Page`` fields: ``arrangement``, ``size_preset``,
        ``orientation``, ``width_mm``/``height_mm`` (custom), ``scale``, ``gap_mm``,
        ``export_members_separately`` …
        """
        page = Page(
            name=name,
            placements=[Placement(device_guid=guid) for guid in member_guids],
            **fields,
        )
        return self.save(page)

    def rename(self, page_id: str, name: str) -> Page:
        return self.save(self._existing(page_id).model_copy(update={"name": name}))

    def duplicate(self, page_id: str) -> Page:
        source = self._existing(page_id)
        copy = Page.model_validate(
            {
                **source.model_dump(mode="json", exclude={"page_id", "updated_at"}),
                "name": copy_name(source.name, {p.name for p in self._pages.values()}),
            }
        )
        return self.save(copy)

    def set_members(self, page_id: str, member_guids: list[str]) -> Page:
        """Replace the members, keeping each existing placement's position and scale."""
        page = self._existing(page_id)
        existing = {p.device_guid: p for p in page.placements}
        placements = [
            existing.get(guid, Placement(device_guid=guid)) for guid in member_guids
        ]
        return self.save(page.model_copy(update={"placements": placements}))

    def arrange(
        self,
        page_id: str,
        arrangement: Arrangement,
        *,
        size_preset: SizePreset | None = None,
        orientation: Orientation | None = None,
    ) -> Page:
        """Re-apply a preset: positions are cleared so the arrangement places them."""
        page = self._existing(page_id)
        update = {
            "arrangement": arrangement,
            "placements": [
                p.model_copy(update={"x_mm": None, "y_mm": None})
                for p in page.placements
            ],
        }
        if size_preset is not None:
            update["size_preset"] = size_preset
        if orientation is not None:
            update["orientation"] = orientation
        return self.save(page.model_copy(update=update))

    def add_note(self, page_id: str, note: PageNote) -> Page:
        page = self._existing(page_id)
        return self.save(page.model_copy(update={"notes": [*page.notes, note]}))

    def remove_member(self, device_guid: str) -> list[str]:
        """Drop a controller from every page. Pages left with fewer than 2 members are
        deleted. Returns the ids of pages that changed or were deleted."""
        changed: list[str] = []
        for page in list(self._pages.values()):
            if device_guid not in page.member_guids:
                continue
            placements = [p for p in page.placements if p.device_guid != device_guid]
            changed.append(page.page_id)
            if len(placements) < 2:
                self.delete(page.page_id)
            else:
                self.save(page.model_copy(update={"placements": placements}))
        return changed

    def delete(self, page_id: str) -> None:
        db_pages.delete_page(page_id)
        self._pages.pop(page_id, None)

    def _existing(self, page_id: str) -> Page:
        page = self._pages.get(page_id)
        if page is None:
            raise ValueError(f"unknown page {page_id!r}")
        return page


if __name__ == "__main__":
    pass
