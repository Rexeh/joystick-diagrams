"""Template.template_path / template_key / content_hash (plan §4.3)."""

import shutil
from hashlib import sha256
from pathlib import Path

from joystick_diagrams.template import (
    Template,
    bundled_templates_root,
    template_key_for,
)

STARTER = Path("templates/Starter Template.svg")
TEST_TEMPLATE = Path("tests/data/template_test.svg")


def test_template_path_is_resolved():
    template = Template(str(TEST_TEMPLATE))
    assert template.template_path == TEST_TEMPLATE.resolve()
    assert template.template_file_name == "template_test.svg"


def test_bundled_key_is_relative_posix():
    # install_root() is "" in development, so the bundled root is ./templates
    assert bundled_templates_root() == (Path(".").resolve() / "templates")
    assert Template(str(STARTER)).template_key == "bundled:Starter Template.svg"
    nested = next(Path("templates/WinWing").rglob("*.svg"))
    assert (
        Template(str(nested)).template_key
        == f"bundled:{nested.relative_to('templates').as_posix()}"
    )


def test_user_key_is_absolute_posix(tmp_path):
    copy = tmp_path / "My Template.svg"
    shutil.copy(TEST_TEMPLATE, copy)
    assert Template(str(copy)).template_key == f"user:{copy.resolve().as_posix()}"
    assert template_key_for(copy) == f"user:{copy.resolve().as_posix()}"


def test_content_hash_is_file_bytes_hash_and_stable_when_raw_data_changes():
    template = Template(str(STARTER))
    expected = sha256(STARTER.read_bytes()).hexdigest()
    assert template.content_hash == expected
    template.raw_data = "changed"
    assert template.content_hash == expected
    assert template.content_hash is template.content_hash  # memoised


def test_content_hash_matches_version_manifest():
    from joystick_diagrams.version import generate_template_manifest

    manifest = generate_template_manifest()
    assert Template(str(STARTER)).content_hash == manifest["Starter Template.svg"]


def test_content_hash_refreshes_when_file_changes(tmp_path):
    copy = tmp_path / "t.svg"
    shutil.copy(TEST_TEMPLATE, copy)
    template = Template(str(copy))
    first = template.content_hash
    copy.write_bytes(copy.read_bytes() + b"\n<!-- edited -->\n")
    assert template.content_hash != first


def test_existing_public_api_unchanged():
    template = Template(str(TEST_TEMPLATE))
    assert template.button_count == 3
    assert template.get_template_buttons() == {"button_1", "button_2", "button_10"}
    assert template.template_name is True
    assert template.date is True
