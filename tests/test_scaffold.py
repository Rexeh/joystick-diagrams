"""Tests for the create-plugin scaffolder."""

from uuid import UUID

import pytest

from joystick_diagrams.plugins import scaffold
from joystick_diagrams.plugins.plugin_installer import validate_plugin


def test_slugify_normalises_names():
    assert scaffold.slugify("My Cool Plugin!") == "my_cool_plugin"
    assert scaffold.slugify("  DCS  World  ") == "dcs_world"
    assert scaffold.slugify("***") == "plugin"


def test_create_parser_plugin_is_loadable(tmp_path):
    dest = scaffold.create_plugin("My Test Plugin", "parser", tmp_path)
    assert dest == tmp_path / "my_test_plugin_plugin"
    assert (dest / "__init__.py").is_file()
    assert (dest / "main.py").is_file()
    assert (dest / "img").is_dir()

    valid, name = validate_plugin(dest, "parser")
    assert valid, name
    assert name == "My Test Plugin"

    # The generated id is a proper UUID and is wired into the loaded plugin.
    module = __import__(
        "joystick_diagrams.plugins.plugin_manager", fromlist=["load_user_parser_plugin"]
    ).load_user_parser_plugin(dest)
    plugin = module.ParserPlugin()
    assert isinstance(plugin.id, UUID)


def test_create_output_plugin_is_loadable(tmp_path):
    dest = scaffold.create_plugin("My Exporter", "output", tmp_path)
    valid, name = validate_plugin(dest, "output")
    assert valid, name
    assert name == "My Exporter"


def test_create_plugin_rejects_unknown_type(tmp_path):
    with pytest.raises(ValueError):
        scaffold.create_plugin("X", "banana", tmp_path)


def test_create_plugin_refuses_existing_dir(tmp_path):
    scaffold.create_plugin("Dupe", "parser", tmp_path)
    with pytest.raises(FileExistsError):
        scaffold.create_plugin("Dupe", "parser", tmp_path)


def test_generated_ids_are_unique(tmp_path):
    a = scaffold.create_plugin("Alpha", "parser", tmp_path)
    b = scaffold.create_plugin("Beta", "parser", tmp_path)
    id_a = (a / "main.py").read_text()
    id_b = (b / "main.py").read_text()
    # Extract the UUID string from each generated PluginMeta and confirm they differ.
    import re

    pat = re.compile(r'id="([0-9a-f-]{36})"')
    assert pat.search(id_a).group(1) != pat.search(id_b).group(1)


def test_cli_main_creates_plugin(tmp_path):
    rc = scaffold.main(["My CLI Plugin", "parser", "--dest", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "my_cli_plugin_plugin" / "main.py").is_file()


def test_cli_main_rejects_bad_type():
    # Argparse rejects an invalid choice (exits non-zero) before create_plugin runs.
    with pytest.raises(SystemExit):
        scaffold.main(["X", "banana"])
