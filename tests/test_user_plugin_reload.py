"""Reloading a user plugin installed again during the session runs its new code."""

import sys

import pytest

from joystick_diagrams.plugins.output_plugin_manager import load_user_output_plugin
from joystick_diagrams.plugins.plugin_manager import load_user_parser_plugin


def write_plugin(folder, value):
    folder.mkdir(exist_ok=True)
    (folder / "__init__.py").write_text("")
    (folder / "main.py").write_text("from .helper import VALUE\n")
    (folder / "helper.py").write_text(f"VALUE = {value!r}\n")


@pytest.mark.parametrize(
    ("loader", "prefix"),
    [
        (load_user_parser_plugin, "jd_user_parser_plugin_"),
        (load_user_output_plugin, "jd_user_output_plugin_"),
    ],
)
def test_reinstalled_plugin_uses_its_new_submodules(tmp_path, loader, prefix):
    plugin = tmp_path / "reload_test_plugin"
    try:
        write_plugin(plugin, "old")
        assert loader(plugin).VALUE == "old"

        # same folder name, new files: what an update through the Store or a ZIP does
        write_plugin(plugin, "new version")
        assert loader(plugin).VALUE == "new version"
    finally:
        for name in [n for n in sys.modules if n.startswith(prefix + plugin.name)]:
            del sys.modules[name]
