"""Hosted plugin catalog client.

Fetches and parses the ``plugins_manifest.json`` catalog hosted on
joystick-diagrams.com, and compares it against the plugins currently installed to
determine what is available to install and which installed plugins have updates.

The manifest is authored/generated website-side (see the feature design); this module
only *consumes* it, and does so defensively — a single malformed entry is dropped and
logged rather than failing the whole catalog.
"""

import logging
from enum import Enum
from typing import Literal
from uuid import UUID

import requests
import semver
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from joystick_diagrams.version import VERSION, VERSION_SERVER

_logger = logging.getLogger(__name__)

CATALOG_FILE = "plugins_manifest.json"
CATALOG_URL = VERSION_SERVER + CATALOG_FILE
_FETCH_TIMEOUT = 5

PluginType = Literal["parser", "output"]


class CatalogEntry(BaseModel):
    """A single plugin listing in the hosted catalog."""

    model_config = ConfigDict(frozen=True)

    id: UUID  # stable identity; malformed values are rejected at parse time
    name: str
    type: PluginType
    version: str
    description: str = ""
    author: str = ""
    signed: bool = False  # display hint: True => 1st-party "Verified"
    download_url: str
    sha256: str
    min_app_version: str | None = None
    icon_url: str | None = None

    @field_validator("version", "min_app_version")
    @classmethod
    def _valid_semver(cls, value: str | None) -> str | None:
        if value is None:
            return value
        semver.Version.parse(value, optional_minor_and_patch=True)
        return value


class PluginCatalog(BaseModel):
    """The parsed catalog document."""

    schema_version: int = 1
    plugins: list[CatalogEntry] = []


class CatalogStatus(str, Enum):
    AVAILABLE = "available"  # not installed
    INSTALLED = "installed"  # installed, up to date
    UPDATE_AVAILABLE = "update_available"  # installed, newer version in catalog


class CatalogItemStatus(BaseModel):
    """A catalog entry paired with its status relative to what is installed."""

    entry: CatalogEntry
    status: CatalogStatus
    installed_version: str | None = None
    compatible: bool = True  # False when the running app is below min_app_version


def fetch_catalog(url: str = CATALOG_URL) -> PluginCatalog | None:
    """Fetch and parse the hosted plugin catalog.

    Returns a PluginCatalog on success, or None on any network/parse failure
    (mirrors version.fetch_remote_manifest's fail-soft behaviour).
    """
    try:
        response = requests.get(url, timeout=_FETCH_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as e:
        _logger.error(f"Unable to reach server for plugin catalog: {e}")
        return None
    except ValueError as e:
        _logger.error(f"Plugin catalog is not valid JSON: {e}")
        return None

    return parse_catalog(payload)


def parse_catalog(payload: dict) -> PluginCatalog:
    """Parse a raw catalog dict, dropping (and logging) any malformed entries."""
    entries: list[CatalogEntry] = []
    for raw in payload.get("plugins", []):
        try:
            entries.append(CatalogEntry(**raw))
        except (ValidationError, TypeError) as e:
            _logger.warning(f"Skipping malformed plugin catalog entry {raw!r}: {e}")

    return PluginCatalog(
        schema_version=payload.get("schema_version", 1), plugins=entries
    )


def installed_index(*managers) -> dict[UUID, str]:
    """Map installed plugin id -> installed version across the given managers.

    Plugins without an id (older, pre-catalog installs) are skipped.
    """
    index: dict[UUID, str] = {}
    for manager in managers:
        for plugin in getattr(manager, "loaded_plugins", []):
            plugin_id = getattr(plugin, "id", None)
            if plugin_id is not None:
                index[plugin_id] = plugin.version
    return index


def compute_status(
    catalog: PluginCatalog,
    installed: dict[UUID, str],
    app_version: str = VERSION,
) -> list[CatalogItemStatus]:
    """Classify every catalog entry against what is installed."""
    results: list[CatalogItemStatus] = []
    for entry in catalog.plugins:
        installed_version = installed.get(entry.id)
        compatible = _is_compatible(app_version, entry.min_app_version)

        if installed_version is None:
            status = CatalogStatus.AVAILABLE
        elif _is_newer(entry.version, installed_version):
            status = CatalogStatus.UPDATE_AVAILABLE
        else:
            status = CatalogStatus.INSTALLED

        results.append(
            CatalogItemStatus(
                entry=entry,
                status=status,
                installed_version=installed_version,
                compatible=compatible,
            )
        )
    return results


def available_updates(statuses: list[CatalogItemStatus]) -> list[CatalogItemStatus]:
    """Filter to only the entries that are installed with a newer version available."""
    return [s for s in statuses if s.status is CatalogStatus.UPDATE_AVAILABLE]


def _is_newer(candidate: str, baseline: str) -> bool:
    """True when candidate semver is strictly greater than baseline."""
    try:
        return semver.Version.parse(
            candidate, optional_minor_and_patch=True
        ) > semver.Version.parse(baseline, optional_minor_and_patch=True)
    except ValueError as e:
        _logger.warning(
            f"Unable to compare versions {candidate!r} vs {baseline!r}: {e}"
        )
        return False


def _is_compatible(app_version: str, min_app_version: str | None) -> bool:
    """True when the running app version satisfies an entry's min_app_version."""
    if min_app_version is None:
        return True
    try:
        return semver.Version.parse(
            app_version, optional_minor_and_patch=True
        ) >= semver.Version.parse(min_app_version, optional_minor_and_patch=True)
    except ValueError:
        return True
