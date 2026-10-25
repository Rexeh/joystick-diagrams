"""Inventory snapshot: which controllers each read produced, so stage 2 can draw
before the next read finishes, and so a controller that comes back with a new
GUID keeps its template.

``record_read(profile_wrappers)`` is called once after a game read (see
``AppState.record_device_read``). It:

1. stamps every controller in the read (``device_inventory`` row and the
   ``devices`` row's ``last_seen``/``games_json``);
2. recomputes the automatic "No diagram" value from the read's facts
   (``device_status.auto_classification``) and stores it with
   ``kind_source == 'auto'``, never touching a ``user`` value;
3. for a GUID never seen before whose normalised name (``normalise_device_name``:
   appended ``{GUID}`` removed, whitespace collapsed, case folded) exactly
   matches a remembered controller that has a template, copies the template,
   kind and layout edits to the new GUID and attaches the notice
   "Kept your template: this controller came back with a new ID". When the old
   GUID is in the same read too, a "possible duplicate" notice is added so the
   screen can offer "Same controller as…". Exact match only, no fuzzy matching.

``is_new(guid)`` is "first seen in the most recent read".
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from joystick_diagrams.db import db_device_inventory
from joystick_diagrams.db.db_device_inventory import InventoryRow
from joystick_diagrams.device_status import (
    DeviceFacts,
    auto_classification,
    collect_device_facts,
)

if TYPE_CHECKING:
    from joystick_diagrams.db.device_service import DeviceService
    from joystick_diagrams.db.layout_service import LayoutService

_logger = logging.getLogger(__name__)

NOTICE_KEPT_TEMPLATE = "kept_template"
NOTICE_POSSIBLE_DUPLICATE = "possible_duplicate"

NOTICE_TEXT = {
    NOTICE_KEPT_TEMPLATE: "Kept your template: this controller came back with a new ID",
    NOTICE_POSSIBLE_DUPLICATE: "Possible duplicate: this may be the same controller as {name}",
}

_GUID_SUFFIX = re.compile(
    r"\s*\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?\s*$"
)


def normalise_device_name(name: str | None) -> str | None:
    """Exact-match key for GUID inheritance: no appended ``{GUID}``, one space, lower case."""
    if not name:
        return None
    cleaned = _GUID_SUFFIX.sub("", name)
    cleaned = " ".join(cleaned.split()).casefold()
    return cleaned or None


@dataclass(frozen=True)
class InventoryNotice:
    code: str
    guid: str  # the controller the notice is attached to (the new GUID)
    related_guid: str | None = None  # the remembered controller it matched
    related_name: str | None = None

    @property
    def text(self) -> str:
        return NOTICE_TEXT.get(self.code, self.code).format(
            name=self.related_name or "another controller"
        )


@dataclass
class ReadResult:
    stamp: str
    seen: list[str] = field(default_factory=list)
    new: list[str] = field(default_factory=list)
    notices: list[InventoryNotice] = field(default_factory=list)
    auto_kinds: dict[str, tuple[str, str]] = field(default_factory=dict)

    @property
    def inherited(self) -> list[InventoryNotice]:
        return [n for n in self.notices if n.code == NOTICE_KEPT_TEMPLATE]

    @property
    def duplicates(self) -> list[InventoryNotice]:
        return [n for n in self.notices if n.code == NOTICE_POSSIBLE_DUPLICATE]


class DeviceInventoryService:
    def __init__(self, device_service: DeviceService, layout_service: LayoutService):
        self.device_service = device_service
        self.layout_service = layout_service
        self._rows: dict[str, InventoryRow] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        self._rows = {row.guid: row for row in db_device_inventory.get_all_rows()}
        _logger.info(f"Loaded {len(self._rows)} remembered controllers from database")

    def _refresh(self, guid: str) -> None:
        row = db_device_inventory.get_row(guid)
        if row is None:
            self._rows.pop(guid, None)
        else:
            self._rows[guid] = row

    # ── Read API ──

    def entry(self, guid: str) -> InventoryRow | None:
        return self._rows.get(guid)

    def known_guids(self) -> list[str]:
        return sorted(self._rows)

    def all_entries(self) -> dict[str, InventoryRow]:
        return dict(self._rows)

    def latest_read(self) -> str | None:
        stamps = [row.last_seen for row in self._rows.values() if row.last_seen]
        return max(stamps) if stamps else None

    def is_new(self, guid: str) -> bool:
        row = self._rows.get(guid)
        latest = self.latest_read()
        return bool(row and latest and row.first_seen == latest)

    def new_guids(self) -> list[str]:
        return sorted(guid for guid in self._rows if self.is_new(guid))

    def notices(self, guid: str) -> list[InventoryNotice]:
        row = self._rows.get(guid)
        if row is None or not row.notices_json:
            return []
        try:
            items = json.loads(row.notices_json)
        except ValueError:
            return []
        return [InventoryNotice(**item) for item in items if isinstance(item, dict)]

    def clear_notices(self, guid: str) -> None:
        db_device_inventory.set_notices(guid, None)
        self._refresh(guid)

    def forget(self, guid: str) -> None:
        db_device_inventory.delete_row(guid)
        self._rows.pop(guid, None)

    # ── Recording a read ──

    def record_read(
        self, profile_wrappers: Iterable[Any], now: datetime | None = None
    ) -> ReadResult:
        """Snapshot the controllers in ``profile_wrappers`` (see module docstring)."""
        stamp = (now or datetime.now(timezone.utc)).isoformat()
        facts = collect_device_facts(profile_wrappers)
        remembered = dict(self._rows)  # before this read
        result = ReadResult(stamp=stamp)

        for guid in sorted(facts):
            entry = facts[guid]
            if guid not in remembered:
                result.new.append(guid)
            result.seen.append(guid)
            self._stamp(guid, entry, stamp)
            self._store_auto_kind(guid, entry, result)

        for guid in result.new:
            self._inherit(guid, facts, remembered, result)
        return result

    def _stamp(self, guid: str, entry: DeviceFacts, stamp: str) -> None:
        db_device_inventory.record_seen(
            guid, entry.name, normalise_device_name(entry.name), stamp
        )
        self._refresh(guid)
        self.device_service.record_seen(guid, entry.name, stamp, entry.games)

    def _store_auto_kind(self, guid: str, entry: DeviceFacts, result: ReadResult):
        auto = auto_classification(entry)
        if auto is None:
            self.device_service.clear_auto_kind(guid)
            return
        kind, reason = auto
        if self.device_service.set_auto_kind(guid, kind, reason, entry.name):
            result.auto_kinds[guid] = (kind, reason)

    # ── GUID inheritance ──

    def _inherit(
        self,
        new_guid: str,
        facts: dict[str, DeviceFacts],
        remembered: dict[str, InventoryRow],
        result: ReadResult,
    ) -> None:
        source = self._match_by_name(new_guid, facts[new_guid].name, remembered)
        if source is None:
            return
        notices = [self._copy_configuration(source.guid, new_guid, source.name)]
        if source.guid in facts:
            notices.append(
                InventoryNotice(
                    NOTICE_POSSIBLE_DUPLICATE, new_guid, source.guid, source.name
                )
            )
        db_device_inventory.set_notices(
            new_guid, json.dumps([asdict(n) for n in notices])
        )
        self._refresh(new_guid)
        result.notices.extend(notices)

    def _match_by_name(
        self, new_guid: str, name: str | None, remembered: dict[str, InventoryRow]
    ) -> InventoryRow | None:
        key = normalise_device_name(name)
        if key is None:
            return None
        matches = [
            row
            for guid, row in remembered.items()
            if guid != new_guid
            and row.normalised_name == key
            and self.device_service.template(guid) is not None
        ]
        if not matches:
            return None
        # Most recently read first; ties by GUID keep it deterministic.
        matches.sort(key=lambda row: (row.last_seen or "", row.guid), reverse=True)
        return matches[0]

    def _copy_configuration(
        self, from_guid: str, to_guid: str, from_name: str | None
    ) -> InventoryNotice:
        template = self.device_service.template(from_guid)
        if template is not None:
            self.device_service.set_template_identity(
                to_guid, template.path, template.key, template.content_hash
            )
            if template.key:
                self.layout_service.copy_device_layers(template.key, from_guid, to_guid)
        self.device_service.copy_kind(from_guid, to_guid)
        _logger.info(
            f"Controller {to_guid[:8]} matched {from_guid[:8]} by name; template kept"
        )
        return InventoryNotice(NOTICE_KEPT_TEMPLATE, to_guid, from_guid, from_name)


if __name__ == "__main__":
    pass
