"""``template_identity``: relink a moved template by name, then by sha256; never delete."""

import shutil
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from joystick_diagrams.db import db_device_management, db_template_layouts
from joystick_diagrams.db.device_service import DeviceService, DeviceTemplateRef
from joystick_diagrams.db.layout_service import LayoutService
from joystick_diagrams.render.layout import HideOp
from joystick_diagrams.template import hash_file_bytes, template_key_for
from joystick_diagrams.template_identity import (
    candidate_templates,
    find_replacement,
    is_template_file,
    relink_device_template,
    resolve_template,
)

GUID = "666ec0a0-556b-11ee-8002-444553540000"
TEST_TEMPLATE = Path("tests/data/template_test.svg")
STARTER = Path("templates/Starter Template.svg")


@pytest.fixture(autouse=True)
def memory_db(tmp_path):
    conn = sqlite3.connect(":memory:")
    with (
        patch(
            "joystick_diagrams.db.db_device_management.connection", return_value=conn
        ),
        patch("joystick_diagrams.db.db_template_layouts.connection", return_value=conn),
        patch(
            "joystick_diagrams.template_identity.user_templates_root",
            return_value=tmp_path / "My templates",
        ),
    ):
        db_device_management.create_new_db_if_not_exist()
        db_template_layouts.create_new_db_if_not_exist()
        yield conn
    conn.close()


def test_is_template_file_skips_drawio_backups():
    assert is_template_file(Path("templates/CH/CH Fighterstick USB.svg"))
    assert not is_template_file(Path("templates/CH/.$CH Fighterstick USB.svg.bkp"))
    assert not is_template_file(Path("templates/readme.txt"))


def test_candidates_include_bundled_then_my_templates(tmp_path):
    mine = tmp_path / "My templates"
    mine.mkdir()
    shutil.copy(TEST_TEMPLATE, mine / "Mine.svg")
    found = candidate_templates()
    assert STARTER.resolve() in found
    assert not any(p.name.endswith(".bkp") for p in found)
    assert found[-1] == mine / "Mine.svg"


def test_find_replacement_by_name_then_hash(tmp_path):
    a = tmp_path / "a" / "Stick.svg"
    b = tmp_path / "b" / "Stick.svg"
    c = tmp_path / "c" / "Renamed.svg"
    for p in (a, b, c):
        p.parent.mkdir()
        shutil.copy(TEST_TEMPLATE, p)
    b.write_bytes(b.read_bytes() + b"\n<!-- edited -->\n")
    digest = hash_file_bytes(a)
    # Several files share the name: the one with the same bytes wins
    assert find_replacement("stick.svg", digest, [b, a, c]) == (a, "filename")
    # Without a hash the first by name is taken
    assert find_replacement("Stick.svg", None, [b, a]) == (b, "filename")
    # No name match: same bytes under another name
    assert find_replacement("Gone.svg", digest, [b, c]) == (c, "hash")
    assert find_replacement("Gone.svg", "nope", [b, c]) is None
    assert find_replacement("Gone.svg", None, [b, c]) is None


def test_resolve_template_statuses(tmp_path):
    assert resolve_template(None).status == "none"
    assert resolve_template(DeviceTemplateRef("", None, None)).status == "none"
    ok = resolve_template(DeviceTemplateRef(str(STARTER), None, None))
    assert ok.status == "ok" and ok.usable
    assert ok.template_key == "bundled:Starter Template.svg"
    assert ok.file_name == "Starter Template.svg"
    missing = resolve_template(
        DeviceTemplateRef(str(tmp_path / "Nope.svg"), "user:/x/Nope.svg", "abc"), []
    )
    assert missing.status == "missing" and not missing.usable
    assert (
        missing.template_key == "user:/x/Nope.svg" and missing.file_name == "Nope.svg"
    )
    # A missing bundled template found again by name among the candidates
    moved = resolve_template(
        DeviceTemplateRef(
            str(tmp_path / "old" / "Starter Template.svg"),
            "user:/old/Starter Template.svg",
            None,
        )
    )
    assert moved.status == "relinked" and moved.relinked_by == "filename"
    assert moved.path == STARTER.resolve()
    assert moved.template_key == "bundled:Starter Template.svg"
    assert moved.previous_key == "user:/old/Starter Template.svg"


def test_relink_device_template_updates_row_and_layouts(tmp_path):
    device_service = DeviceService()
    layout_service = LayoutService()
    old = tmp_path / "old" / "Gladiator.svg"
    old.parent.mkdir()
    shutil.copy(TEST_TEMPLATE, old)
    device_service.set_template(GUID, old)
    old_key = template_key_for(old)
    layout_service.append_op(
        old_key, "", HideOp(target="button_1"), "h", device_guid=GUID
    )

    # Still there: nothing changes
    assert relink_device_template(GUID, device_service, layout_service).status == "ok"

    mine = tmp_path / "My templates"
    mine.mkdir()
    new = mine / "Gladiator renamed.svg"
    shutil.move(old, new)
    result = relink_device_template(GUID, device_service, layout_service)
    assert result.status == "relinked" and result.relinked_by == "hash"
    ref = device_service.template(GUID)
    assert ref.path == str(new) and ref.key == template_key_for(new)
    assert ref.content_hash == hash_file_bytes(new)
    assert layout_service.has_ops(ref.key, None, GUID)
    assert not layout_service.has_ops(old_key, None, GUID)

    # Gone for good: reported, never deleted
    new.unlink()
    gone = relink_device_template(GUID, device_service, layout_service)
    assert gone.status == "missing" and gone.file_name == "Gladiator renamed.svg"
    assert device_service.template(GUID) == ref


def test_relink_without_a_template_is_none():
    assert relink_device_template(GUID, DeviceService()).status == "none"
