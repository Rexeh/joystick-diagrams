"""Tests for the hosted plugin catalog client."""

from uuid import UUID, uuid4

import pytest
import requests
from pydantic import ValidationError

from joystick_diagrams.plugins import plugin_catalog as pc
from joystick_diagrams.plugins.plugin_settings import PluginMeta

DCS_ID = "ea2a7f6a-cbf3-4f81-91ed-fdc81dd13af8"
OKB_ID = "1f1ce378-f17c-42fa-ab3e-7b1fc4cf2989"


def _entry(**overrides) -> dict:
    base = {
        "id": str(uuid4()),
        "name": "Some Plugin",
        "type": "parser",
        "version": "1.0.0",
        "download_url": "https://example.com/p.zip",
        "sha256": "0" * 64,
    }
    base.update(overrides)
    return base


class _FakeManager:
    def __init__(self, loaded_plugins):
        self.loaded_plugins = loaded_plugins


class _FakePlugin:
    def __init__(self, plugin_id, version):
        self.id = plugin_id
        self.version = version


# ── Model validation ──


def test_catalog_entry_valid():
    entry = pc.CatalogEntry(**_entry(id=DCS_ID, version="2.1.0"))
    assert isinstance(entry.id, UUID)
    assert entry.signed is False  # defaults


def test_catalog_entry_rejects_malformed_id():
    with pytest.raises(ValidationError):
        pc.CatalogEntry(**_entry(id="not-a-uuid"))


def test_catalog_entry_rejects_bad_semver():
    with pytest.raises(ValidationError):
        pc.CatalogEntry(**_entry(version="banana"))


def test_plugin_meta_valid_and_idless_and_malformed():
    assert isinstance(
        PluginMeta(id=DCS_ID, name="X", version="1.0.0", icon_path="i.ico").id, UUID
    )
    assert PluginMeta(name="X", version="1.0.0", icon_path="i.ico").id is None
    with pytest.raises(ValidationError):
        PluginMeta(id="nope", name="X", version="1.0.0", icon_path="i.ico")


# ── parse_catalog ──


def test_parse_catalog_drops_malformed_entries(caplog):
    payload = {
        "schema_version": 1,
        "plugins": [
            _entry(id=DCS_ID),
            _entry(id="broken"),  # invalid uuid → dropped
            _entry(version="not-semver"),  # invalid version → dropped
        ],
    }
    catalog = pc.parse_catalog(payload)
    assert len(catalog.plugins) == 1
    assert str(catalog.plugins[0].id) == DCS_ID


def test_parse_catalog_empty():
    assert pc.parse_catalog({}).plugins == []


# ── installed_index ──


def test_installed_index_skips_idless_plugins():
    dcs = _FakePlugin(UUID(DCS_ID), "2.0.0")
    idless = _FakePlugin(None, "1.0.0")
    parser_mgr = _FakeManager([dcs, idless])
    output_mgr = _FakeManager([])
    index = pc.installed_index(parser_mgr, output_mgr)
    assert index == {UUID(DCS_ID): "2.0.0"}


# ── compute_status ──


def test_compute_status_classifies_all_cases():
    catalog = pc.parse_catalog(
        {
            "plugins": [
                _entry(id=DCS_ID, name="DCS", version="2.1.0"),  # update
                _entry(id=OKB_ID, name="OKB", version="1.0.0"),  # installed/current
                _entry(name="New", version="0.1.0"),  # available (not installed)
            ]
        }
    )
    installed = {UUID(DCS_ID): "2.0.0", UUID(OKB_ID): "1.0.0"}
    by_name = {s.entry.name: s for s in pc.compute_status(catalog, installed)}

    assert by_name["DCS"].status is pc.CatalogStatus.UPDATE_AVAILABLE
    assert by_name["DCS"].installed_version == "2.0.0"
    assert by_name["OKB"].status is pc.CatalogStatus.INSTALLED
    assert by_name["New"].status is pc.CatalogStatus.AVAILABLE


def test_compute_status_marks_incompatible():
    catalog = pc.parse_catalog(
        {"plugins": [_entry(name="Future", min_app_version="9.9.9")]}
    )
    statuses = pc.compute_status(catalog, {}, app_version="2.2.1")
    assert statuses[0].compatible is False


def test_available_updates_filters_correctly():
    catalog = pc.parse_catalog(
        {
            "plugins": [
                _entry(id=DCS_ID, version="2.1.0"),
                _entry(id=OKB_ID, version="1.0.0"),
            ]
        }
    )
    installed = {UUID(DCS_ID): "2.0.0", UUID(OKB_ID): "1.0.0"}
    updates = pc.available_updates(pc.compute_status(catalog, installed))
    assert [str(u.entry.id) for u in updates] == [DCS_ID]


# ── fetch_catalog ──


def test_fetch_catalog_network_failure_returns_none(monkeypatch, caplog):
    def boom(*args, **kwargs):
        raise requests.exceptions.RequestException("no network")

    monkeypatch.setattr(requests, "get", boom)
    assert pc.fetch_catalog() is None
    assert "Unable to reach server for plugin catalog" in caplog.text


def test_fetch_catalog_parses_payload(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"plugins": [_entry(id=DCS_ID, name="DCS")]}

    monkeypatch.setattr(requests, "get", lambda *a, **k: MockResponse())
    catalog = pc.fetch_catalog()
    assert catalog is not None
    assert len(catalog.plugins) == 1
    assert catalog.plugins[0].name == "DCS"
