"""Keep a controller's template choice when the template file moves.

A device row stores the template's path, its stable ``template_key``
(``bundled:<relpath>`` / ``user:<abs>``, see ``template.template_key_for``) and
the sha256 of the file when it was chosen. When the path no longer exists,
``resolve_template`` looks for the same file among the templates included with
the app and in My templates, first by file name and then by sha256, and reports
``relinked`` with the new path; only when nothing matches is it ``missing``.
Nothing is deleted: a missing template is a status the screens show ("Choose
template…"), not a silent reset.

``relink_device_template`` applies a ``relinked`` result: the device row gets the
new path and key and the controller's layout edits follow (``LayoutService.relink``).

F1b's ``template_catalog`` enumerates the same folders for the picker; this
module keeps its own small walk so the two can be built independently.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from joystick_diagrams.template import (
    bundled_templates_root,
    hash_file_bytes,
    template_key_for,
)
from joystick_diagrams.utils import user_templates_root

if TYPE_CHECKING:
    from joystick_diagrams.db.device_service import DeviceService, DeviceTemplateRef
    from joystick_diagrams.db.layout_service import LayoutService

_logger = logging.getLogger(__name__)

TEMPLATE_SUFFIX = ".svg"
BACKUP_SUFFIX = ".bkp"

ResolutionStatus = Literal["none", "ok", "relinked", "missing"]
RelinkMethod = Literal["filename", "hash"]


@dataclass(frozen=True)
class TemplateResolution:
    """Outcome of looking up a stored template choice."""

    status: ResolutionStatus
    path: Path | None = None
    template_key: str | None = None
    previous_key: str | None = None
    relinked_by: RelinkMethod | None = None
    file_name: str | None = None  # the stored file's name (shown when missing)

    @property
    def usable(self) -> bool:
        return self.status in ("ok", "relinked")


NONE_RESOLUTION = TemplateResolution(status="none")


def is_template_file(path: Path) -> bool:
    """A ``.svg`` that is not a draw.io backup (``.$name.svg.bkp``)."""
    if path.suffix.lower() != TEMPLATE_SUFFIX:
        return False
    return not any(part.endswith(BACKUP_SUFFIX) for part in path.parts)


def candidate_templates() -> list[Path]:
    """Every template file included with the app, then every one in My templates."""
    found: list[Path] = []
    for root in (bundled_templates_root(), user_templates_root()):
        if not root.is_dir():
            continue
        found.extend(
            sorted(p for p in root.rglob(f"*{TEMPLATE_SUFFIX}") if is_template_file(p))
        )
    return found


def find_replacement(
    file_name: str,
    content_hash: str | None,
    candidates: Iterable[Path],
) -> tuple[Path, RelinkMethod] | None:
    """The file that replaces a vanished template: same name first, then same bytes."""
    candidates = list(candidates)
    by_name = [c for c in candidates if c.name.lower() == file_name.lower()]
    if by_name:
        if len(by_name) > 1 and content_hash:
            same_bytes = [c for c in by_name if _safe_hash(c) == content_hash]
            if same_bytes:
                return same_bytes[0], "filename"
        return by_name[0], "filename"
    if content_hash:
        for candidate in candidates:
            if _safe_hash(candidate) == content_hash:
                return candidate, "hash"
    return None


def _safe_hash(path: Path) -> str | None:
    try:
        return hash_file_bytes(path)
    except OSError:
        return None


def resolve_template(
    ref: DeviceTemplateRef | None,
    candidates: Iterable[Path] | None = None,
) -> TemplateResolution:
    """Resolve a stored template choice to a file on disk (no writes)."""
    if ref is None or not ref.path:
        return NONE_RESOLUTION
    path = Path(ref.path)
    key = ref.key or template_key_for(path)
    if path.is_file():
        return TemplateResolution("ok", path, key, key, None, path.name)
    replacement = find_replacement(
        path.name,
        ref.content_hash,
        candidate_templates() if candidates is None else candidates,
    )
    if replacement is None:
        return TemplateResolution("missing", None, key, key, None, path.name)
    new_path, method = replacement
    return TemplateResolution(
        "relinked", new_path, template_key_for(new_path), key, method, path.name
    )


def relink_device_template(
    guid: str,
    device_service: DeviceService,
    layout_service: LayoutService | None = None,
    candidates: Iterable[Path] | None = None,
) -> TemplateResolution:
    """Resolve ``guid``'s template and, when it moved, re-point the row and its layouts."""
    resolution = resolve_template(device_service.template(guid), candidates)
    if resolution.status != "relinked" or resolution.path is None:
        return resolution
    _logger.info(
        f"Template for {guid[:8]} moved: {resolution.file_name} found again by "
        f"{resolution.relinked_by} at {resolution.path}"
    )
    device_service.set_template_identity(
        guid,
        str(resolution.path),
        resolution.template_key,
        _safe_hash(resolution.path),
    )
    if (
        layout_service is not None
        and resolution.previous_key
        and resolution.previous_key != resolution.template_key
        and layout_service.layers_of_template(resolution.previous_key)
    ):
        layout_service.relink(resolution.previous_key, resolution.template_key)
    return resolution


if __name__ == "__main__":
    pass
