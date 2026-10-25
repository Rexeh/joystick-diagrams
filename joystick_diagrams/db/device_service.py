"""Cached, write-through access to the ``devices`` table.

One ``DeviceRow`` per GUID is loaded once; every write goes to the database and
the cache together. Screens read classification, template identity and the
inventory stamps from here (``device_status.device_status`` does), and the
legacy ``is_hidden``/``set_hidden`` API keeps working: hidden now means
``kind == 'other'`` ("No diagram").

Classification rules (owner decision, no name-based guessing):

- ``set_user_kind`` records the user's choice (``kind_source == 'user'``). The
  app never overwrites it; ``set_auto_kind`` returns ``False`` instead.
- ``set_auto_kind`` / ``clear_auto_kind`` are called by the inventory snapshot
  after every read with the facts of that read (nothing bound, game-declared
  keyboard/mouse). ``device_status`` recomputes the same facts live and only
  trusts a stored ``user`` kind, so a stale ``auto`` value never shows.
- ``set_make_diagram(guid, False)`` is the "Make a diagram for this controller"
  checkbox: a user ``other``. ``True`` records a user ``joystick`` so a declared
  keyboard the user wants drawn stays drawn.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from joystick_diagrams.db import db_device_management
from joystick_diagrams.db.db_device_management import (
    KIND_OTHER,
    KIND_SOURCE_AUTO,
    KIND_SOURCE_USER,
    NO_DIAGRAM_KINDS,
    DeviceRow,
)

_logger = logging.getLogger(__name__)

KIND_JOYSTICK = "joystick"
KIND_REASON_USER = "user"


@dataclass(frozen=True)
class DeviceKind:
    kind: str | None
    source: str | None  # 'user' | 'auto' | None
    reason: str | None

    @property
    def is_user(self) -> bool:
        return self.source == KIND_SOURCE_USER

    @property
    def no_diagram(self) -> bool:
        return self.kind in NO_DIAGRAM_KINDS


@dataclass(frozen=True)
class DeviceTemplateRef:
    path: str
    key: str | None
    content_hash: str | None


class DeviceService:
    def __init__(self):
        self._rows: dict[str, DeviceRow] = {}
        self._load_cache()

    def _load_cache(self):
        self._rows = {
            row.guid: row for row in db_device_management.get_all_device_rows()
        }
        hidden = sum(1 for row in self._rows.values() if row.hidden)
        _logger.info(
            f"Loaded {len(self._rows)} devices from database ({hidden} with no diagram)"
        )

    # ── Rows ──

    def reload(self) -> None:
        """Re-read every row (after code that writes the table directly)."""
        self._load_cache()

    def _refresh(self, guid: str) -> DeviceRow | None:
        row = db_device_management.get_device_row(guid)
        if row is None:
            self._rows.pop(guid, None)
        else:
            self._rows[guid] = row
        return row

    def row(self, guid: str) -> DeviceRow | None:
        return self._rows.get(guid)

    def all_rows(self) -> dict[str, DeviceRow]:
        return dict(self._rows)

    # ── Legacy hidden API ──

    def is_hidden(self, guid: str) -> bool:
        row = self._rows.get(guid)
        return bool(row and row.hidden)

    def set_hidden(self, guid: str, name: str, hidden: bool) -> None:
        db_device_management.set_device_hidden(guid, name, hidden)
        self._refresh(guid)

    def get_all_hidden(self) -> dict[str, str]:
        """Returns dict of guid -> name for all hidden devices."""
        return {
            guid: (row.name or guid) for guid, row in self._rows.items() if row.hidden
        }

    # ── Classification ──

    def kind(self, guid: str) -> DeviceKind | None:
        row = self._rows.get(guid)
        if row is None or row.kind is None:
            return None
        return DeviceKind(row.kind, row.kind_source, row.kind_reason)

    def set_user_kind(
        self, guid: str, kind: str | None, reason: str = KIND_REASON_USER
    ) -> None:
        """Record the user's choice; ``None`` returns the device to automatic."""
        if kind is None:
            db_device_management.set_device_kind(guid, None, None, None)
        else:
            db_device_management.set_device_kind(guid, kind, KIND_SOURCE_USER, reason)
        self._refresh(guid)

    def set_make_diagram(self, guid: str, make: bool, name: str | None = None) -> None:
        kind = KIND_JOYSTICK if make else KIND_OTHER
        db_device_management.set_device_kind(
            guid, kind, KIND_SOURCE_USER, KIND_REASON_USER, name
        )
        self._refresh(guid)

    def set_auto_kind(
        self, guid: str, kind: str, reason: str, name: str | None = None
    ) -> bool:
        """Store an automatic classification unless the user has chosen one."""
        current = self.kind(guid)
        if current is not None and current.is_user:
            return False
        if current is not None and (current.kind, current.reason) == (kind, reason):
            return True
        db_device_management.set_device_kind(guid, kind, KIND_SOURCE_AUTO, reason, name)
        self._refresh(guid)
        return True

    def clear_auto_kind(self, guid: str) -> None:
        current = self.kind(guid)
        if current is None or current.is_user:
            return
        db_device_management.set_device_kind(guid, None, None, None)
        self._refresh(guid)

    def copy_kind(self, from_guid: str, to_guid: str) -> None:
        source = self.kind(from_guid)
        if source is None or source.kind is None:
            return
        db_device_management.set_device_kind(
            to_guid, source.kind, source.source, source.reason
        )
        self._refresh(to_guid)

    # ── Template ──

    def template(self, guid: str) -> DeviceTemplateRef | None:
        """The chosen template (read through: other code still writes paths directly)."""
        row = self._refresh(guid)
        if row is None or not row.template_path:
            return None
        return DeviceTemplateRef(row.template_path, row.template_key, row.template_hash)

    def set_template(self, guid: str, path: Path | str) -> DeviceTemplateRef | None:
        db_device_management.add_update_device_template_path(guid, str(path))
        self._refresh(guid)
        return self.template(guid)

    def set_template_identity(
        self, guid: str, path: str, key: str | None, content_hash: str | None
    ) -> None:
        db_device_management.set_device_template(guid, path, key, content_hash)
        self._refresh(guid)

    def clear_template(self, guid: str) -> None:
        db_device_management.remove_template_path_from_device(guid)
        self._refresh(guid)

    def devices_using_template(self, template_key: str) -> list[str]:
        self.reload()
        return sorted(
            guid for guid, row in self._rows.items() if row.template_key == template_key
        )

    def devices_with_template(self) -> dict[str, DeviceTemplateRef]:
        self.reload()
        return {
            guid: DeviceTemplateRef(
                row.template_path, row.template_key, row.template_hash
            )
            for guid, row in self._rows.items()
            if row.template_path
        }

    # ── Seen / games ──

    def record_seen(
        self, guid: str, name: str | None, last_seen: str, games: dict[str, int]
    ) -> None:
        db_device_management.set_device_seen(guid, name, last_seen, games)
        self._refresh(guid)

    def last_seen(self, guid: str) -> str | None:
        row = self._rows.get(guid)
        return row.last_seen if row else None

    def games(self, guid: str) -> dict[str, int]:
        row = self._rows.get(guid)
        return row.games if row else {}

    # ── Custom device names ──

    def resolve_name(self, guid: str, original_name: str) -> str:
        """Return custom name if set, otherwise the original name."""
        return self.get_custom_name(guid) or original_name

    def get_custom_name(self, guid: str) -> str | None:
        row = self._rows.get(guid)
        return row.custom_name if row and row.custom_name else None

    def set_custom_name(self, guid: str, custom_name: str | None) -> None:
        db_device_management.set_device_custom_name(guid, custom_name or None)
        self._refresh(guid)
