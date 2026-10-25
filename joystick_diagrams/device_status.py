"""One status per controller, computed the same way on every screen.

``device_status(guid, profile_wrappers)`` answers "what does this controller
need?" for stage 2 (Controllers), the Export list, the results card and the
stage strip, so their counts always agree. ``all_device_statuses`` does it for
every controller in the latest read plus the ones the inventory remembers.

States (``DeviceStatus``)
-------------------------
- ``MERGED``: listed under another controller ("Same controller as…").
- ``NOT_SEEN``: remembered from an earlier read, not in the latest one.
- ``NO_PROFILES``: nothing is known about it (no read has produced it).
- ``NO_DIAGRAM``: not drawn. Set by the user (``kind_source == 'user'``), or
  automatically for one fact only: nothing is bound after routing and
  merging. There is no name-based guessing. The automatic value is recomputed
  from the live profiles on every call; a stored ``user`` value is never
  overwritten (``DeviceService``).
- ``NEEDS_TEMPLATE`` / ``TEMPLATE_MISSING`` / ``READY_WITH_GAPS`` / ``READY``:
  the template chain. A vanished file is relinked by name or sha256
  (``template_identity``) before it is reported missing.

``StatusInfo.reason`` is a machine code; ``reason_text`` turns it into the
sentence shown next to the decision, in the app's language
(``docs/superpowers/specs/2026-10-25-ux-language.md``).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.input.device import Device_
from joystick_diagrams.template import Template
from joystick_diagrams.template_identity import (
    TemplateResolution,
    relink_device_template,
    resolve_template,
)

if TYPE_CHECKING:
    from joystick_diagrams.db.device_alias_service import DeviceAliasService
    from joystick_diagrams.db.device_service import DeviceService
    from joystick_diagrams.db.layout_service import LayoutService

_logger = logging.getLogger(__name__)

KIND_NO_DIAGRAM = "other"

# Reason codes
REASON_NOTHING_BOUND = "nothing_bound"
REASON_NOTHING_BOUND_MOVED = "nothing_bound_moved"
REASON_USER = "user"
REASON_LEGACY_HIDDEN = "legacy_hidden"
REASON_MERGED = "merged_into"
REASON_NOT_SEEN = "not_seen"
REASON_NO_PROFILES = "no_profiles"
REASON_TEMPLATE_MISSING = "template_missing"
REASON_TEMPLATE_UNREADABLE = "template_unreadable"


class DeviceStatus(str, Enum):
    NO_PROFILES = "no_profiles"
    NEEDS_TEMPLATE = "needs_template"
    READY = "ready"
    READY_WITH_GAPS = "ready_with_gaps"
    TEMPLATE_MISSING = "template_missing"
    NO_DIAGRAM = "no_diagram"
    NOT_SEEN = "not_seen"
    MERGED = "merged"

    @property
    def exports(self) -> bool:
        """Whether a diagram is produced for this controller."""
        return self in (DeviceStatus.READY, DeviceStatus.READY_WITH_GAPS)


@dataclass(frozen=True)
class StatusInfo:
    state: DeviceStatus
    reason: str | None = None
    profile_count: int = 0
    games: dict[str, int] = field(default_factory=dict)
    template_key: str | None = None
    template_name: str | None = None
    template_path: str | None = None
    missing_controls: list[str] = field(default_factory=list)
    is_new: bool = False
    name: str | None = None
    merged_into: str | None = None
    kind_source: str | None = None  # 'user' | 'auto' | None

    @property
    def reason_text(self) -> str | None:
        return reason_text(self.reason, self.template_name)


# ── Facts gathered from the profiles ──


@dataclass
class DeviceFacts:
    """What the latest read says about one controller (before any decision)."""

    guid: str
    name: str | None = None
    seen_in_read: bool = False  # in some profile before routing/merging
    routed_away: bool = False  # a route moved its bindings to another controller
    bound: list[tuple[str, str]] = field(default_factory=list)  # (game, profile_key)
    devices: list[tuple[Any, Device_]] = field(
        default_factory=list
    )  # (wrapper, device)

    @property
    def profile_count(self) -> int:
        return len(self.bound)

    @property
    def games(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for game, _profile in self.bound:
            counts[game] = counts.get(game, 0) + 1
        return counts


def has_bound_controls(device: Device_) -> bool:
    inputs = getattr(device, "inputs", None)
    if not isinstance(inputs, dict):
        return False
    return any(len(group) > 0 for group in inputs.values())


def _devices_of(profile: Any) -> dict[str, Device_]:
    devices = getattr(profile, "devices", None)
    return devices if isinstance(devices, dict) else {}


def _game_of(wrapper: Any) -> str:
    origin = getattr(wrapper, "profile_origin", None)
    name = getattr(origin, "name", None)
    return name if isinstance(name, str) else ""


def _note_device(facts: DeviceFacts, device: Device_, game: str) -> None:
    facts.seen_in_read = True
    if not facts.name and getattr(device, "name", None):
        facts.name = device.name


def collect_device_facts(profile_wrappers: Iterable[Any]) -> dict[str, DeviceFacts]:
    """Facts per GUID from the raw profiles (``original_profile``) and the
    processed ones (``profile``, after inheritance, routing and merging)."""
    facts: dict[str, DeviceFacts] = {}
    for wrapper in profile_wrappers:
        game = _game_of(wrapper)
        original = getattr(wrapper, "original_profile", None)
        for guid, device in _devices_of(original).items():
            _note_device(facts.setdefault(guid, DeviceFacts(guid)), device, game)
        routes = getattr(original, "input_routes", None)
        if isinstance(routes, dict):
            for route_key in routes:
                source = getattr(route_key, "device_guid", None)
                if source in facts:
                    facts[source].routed_away = True
        processed = getattr(wrapper, "profile", None)
        profile_key = getattr(wrapper, "profile_key", "")
        for guid, device in _devices_of(processed).items():
            entry = facts.setdefault(guid, DeviceFacts(guid))
            _note_device(entry, device, game)
            if has_bound_controls(device):
                entry.bound.append((game, str(profile_key)))
                entry.devices.append((wrapper, device))
    return facts


def auto_classification(facts: DeviceFacts) -> tuple[str, str] | None:
    """``(kind, reason)`` when the facts alone say "No diagram", else ``None``."""
    if facts.seen_in_read and not facts.bound:
        reason = (
            REASON_NOTHING_BOUND_MOVED if facts.routed_away else REASON_NOTHING_BOUND
        )
        return KIND_NO_DIAGRAM, reason
    return None


# ── Sources ──


@dataclass
class StatusSources:
    """The services ``device_status`` reads; ``from_app_state`` builds the usual set."""

    device_service: DeviceService
    alias_service: DeviceAliasService | None = None
    inventory: Any = None  # DeviceInventoryService (``is_new``/``entry``), optional
    layout_service: LayoutService | None = None
    template_cache: dict[str, Template] = field(default_factory=dict)
    relink: bool = True  # write relinked paths back (False: read-only resolution)

    @classmethod
    def from_app_state(cls) -> StatusSources:
        from joystick_diagrams.app_state import AppState

        state = AppState()
        return cls(
            device_service=state.device_service,
            alias_service=state.device_alias_service,
            inventory=getattr(state, "device_inventory_service", None),
            layout_service=state.layout_service,
        )

    def resolve_template(self, guid: str) -> TemplateResolution:
        if self.relink:
            return relink_device_template(
                guid, self.device_service, self.layout_service
            )
        return resolve_template(self.device_service.template(guid))

    def load_template(self, path: str) -> Template | None:
        template = self.template_cache.get(path)
        if template is None:
            try:
                template = Template(path)
            except JoystickDiagramsError as error:
                _logger.warning(f"Template {path} could not be read: {error}")
                return None
            self.template_cache[path] = template
        return template

    def is_new(self, guid: str) -> bool:
        return bool(self.inventory is not None and self.inventory.is_new(guid))

    def known(self, guid: str) -> bool:
        if self.inventory is not None and self.inventory.entry(guid) is not None:
            return True
        return self.device_service.row(guid) is not None

    def known_guids(self) -> set[str]:
        guids = set(self.device_service.all_rows())
        if self.inventory is not None:
            guids.update(self.inventory.known_guids())
        return guids


# ── Status ──


def device_status(
    guid: str,
    profile_wrappers: Iterable[Any],
    sources: StatusSources | None = None,
    facts: dict[str, DeviceFacts] | None = None,
) -> StatusInfo:
    """The status of one controller. ``facts`` may be shared across calls
    (``collect_device_facts``) so a screen computes them once."""
    sources = sources or StatusSources.from_app_state()
    facts = collect_device_facts(profile_wrappers) if facts is None else facts
    entry = facts.get(guid)
    common = _common_fields(guid, entry, sources)

    canonical = sources.alias_service.resolve(guid) if sources.alias_service else guid
    if canonical != guid:
        return StatusInfo(
            DeviceStatus.MERGED, REASON_MERGED, merged_into=canonical, **common
        )
    if entry is None or not entry.seen_in_read:
        if sources.known(guid):
            return StatusInfo(DeviceStatus.NOT_SEEN, REASON_NOT_SEEN, **common)
        return StatusInfo(DeviceStatus.NO_PROFILES, REASON_NO_PROFILES, **common)

    kind = sources.device_service.kind(guid)
    if kind is not None and kind.is_user:
        if kind.no_diagram:
            return StatusInfo(
                DeviceStatus.NO_DIAGRAM,
                kind.reason or REASON_USER,
                kind_source=kind.source,
                **common,
            )
    else:
        auto = auto_classification(entry)
        if auto is not None:
            return StatusInfo(
                DeviceStatus.NO_DIAGRAM, auto[1], kind_source="auto", **common
            )
    return _template_status(guid, entry, sources, common)


def _common_fields(
    guid: str, entry: DeviceFacts | None, sources: StatusSources
) -> dict[str, Any]:
    row = sources.device_service.row(guid)
    name = (entry.name if entry else None) or (row.name if row else None)
    return {
        "name": sources.device_service.resolve_name(guid, name) if name else name,
        "is_new": sources.is_new(guid),
        "profile_count": entry.profile_count if entry else 0,
        "games": entry.games if entry else (row.games if row else {}),
    }


def _template_status(
    guid: str, entry: DeviceFacts, sources: StatusSources, common: dict[str, Any]
) -> StatusInfo:
    ref = sources.device_service.template(guid)
    if ref is None:
        return StatusInfo(DeviceStatus.NEEDS_TEMPLATE, **common)
    resolution = sources.resolve_template(guid)
    template_fields = {
        "template_key": resolution.template_key or ref.key,
        "template_name": resolution.file_name,
        "template_path": str(resolution.path) if resolution.path else ref.path,
    }
    if not resolution.usable or resolution.path is None:
        return StatusInfo(
            DeviceStatus.TEMPLATE_MISSING,
            REASON_TEMPLATE_MISSING,
            **template_fields,
            **common,
        )
    template = sources.load_template(str(resolution.path))
    if template is None:
        return StatusInfo(
            DeviceStatus.TEMPLATE_MISSING,
            REASON_TEMPLATE_UNREADABLE,
            **template_fields,
            **common,
        )
    missing = missing_controls(entry, template)
    state = DeviceStatus.READY_WITH_GAPS if missing else DeviceStatus.READY
    return StatusInfo(state, missing_controls=missing, **template_fields, **common)


def missing_controls(entry: DeviceFacts, template: Template) -> list[str]:
    """Controls bound in any profile that the template has no box for."""
    missing: set[str] = set()
    for wrapper, device in entry.devices:
        missing.update(ExportDevice(device, template, wrapper).check_compatibility())
    return sorted(missing)


def all_device_statuses(
    profile_wrappers: Iterable[Any],
    sources: StatusSources | None = None,
    *,
    include_unseen: bool = True,
) -> dict[str, StatusInfo]:
    """Status for every controller in the read (and, by default, every remembered one)."""
    sources = sources or StatusSources.from_app_state()
    wrappers = list(profile_wrappers)
    facts = collect_device_facts(wrappers)
    guids = set(facts)
    if include_unseen:
        guids.update(sources.known_guids())
    return {
        guid: device_status(guid, wrappers, sources, facts) for guid in sorted(guids)
    }


# ── Words ──


def reason_text(
    reason: str | None,
    template_name: str | None = None,
    merged_name: str | None = None,
) -> str | None:
    """The plain sentence shown next to a decision, or ``None`` when there is none.

    This is the only place reason codes become words; every screen (2. Controllers,
    the results card in 1. Setup, the "No diagram:" line in Export) uses it. The
    wording follows ``docs/superpowers/specs/2026-10-25-ux-language.md`` (boards
    J03–J06): "Nothing bound: its bindings are on your stick", "Set by you".
    Callers that put the reason inside brackets lower its first letter.
    """
    if not reason:
        return None
    if reason == REASON_TEMPLATE_MISSING:
        return (
            f"Template {template_name} can't be found"
            if template_name
            else "Template can't be found"
        )
    if reason == REASON_MERGED and merged_name:
        return f"Same controller as {merged_name}"
    text = _FIXED_REASONS.get(reason, reason.replace("_", " "))
    return text[:1].upper() + text[1:]


_FIXED_REASONS = {
    REASON_NOTHING_BOUND: "Nothing bound",
    REASON_NOTHING_BOUND_MOVED: "Nothing bound: its bindings are on your stick",
    REASON_USER: "Set by you",
    REASON_LEGACY_HIDDEN: "Set by you",
    REASON_MERGED: "Listed twice: its bindings go on one diagram",
    REASON_NOT_SEEN: "Not in your latest bindings",
    REASON_NO_PROFILES: "No bindings read yet",
    REASON_TEMPLATE_UNREADABLE: "Template can't be read",
}


if __name__ == "__main__":
    pass
