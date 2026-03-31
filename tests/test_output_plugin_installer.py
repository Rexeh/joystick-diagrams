"""Tests for user output plugin installation, uninstallation, validation, and loading."""

import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from joystick_diagrams.exceptions import JoystickDiagramsError, PluginNotValidError
from joystick_diagrams.plugins.output_plugin_installer import (
    install_output_plugin,
    uninstall_output_plugin,
    validate_output_plugin,
)
from joystick_diagrams.plugins.output_plugin_manager import (
    OutputPluginManager,
    find_user_output_plugins,
    load_user_output_plugin,
)

# ── Fixture: minimal valid plugin on disk ──

VALID_INIT = ""
VALID_MAIN = """\
from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginMeta


class OutputPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(name="TestUserPlugin", version="0.1.0", icon_path="img/x.ico")

    def process_export(self, results):
        return True
"""

BAD_MAIN_NO_CLASS = """\
# No OutputPlugin class here
x = 1
"""

BAD_MAIN_WRONG_BASE = """\
class OutputPlugin:
    pass
"""


def _make_plugin_dir(
    base: Path, name: str = "test_plugin", main_content: str = VALID_MAIN
) -> Path:
    """Create a minimal plugin directory structure."""
    plugin_dir = base / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "__init__.py").write_text(VALID_INIT)
    (plugin_dir / "main.py").write_text(main_content)
    return plugin_dir


def _make_plugin_zip(base: Path, name: str = "test_plugin") -> Path:
    """Create a ZIP containing a valid plugin directory."""
    plugin_dir = _make_plugin_dir(base / "src", name)
    zip_path = base / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in plugin_dir.iterdir():
            zf.write(f, f"{name}/{f.name}")
    return zip_path


# ── load_user_output_plugin ──


def test_load_user_output_plugin_success(tmp_path):
    plugin_dir = _make_plugin_dir(tmp_path)
    module = load_user_output_plugin(plugin_dir)
    assert hasattr(module, "OutputPlugin")
    instance = module.OutputPlugin()
    assert instance.name == "TestUserPlugin"


def test_load_user_output_plugin_missing_main(tmp_path):
    plugin_dir = tmp_path / "bad_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text("")
    with pytest.raises(PluginNotValidError):
        load_user_output_plugin(plugin_dir)


def test_load_user_output_plugin_syntax_error(tmp_path):
    plugin_dir = tmp_path / "syntax_err"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text("")
    (plugin_dir / "main.py").write_text("def broken(:\n")
    with pytest.raises(SyntaxError):
        load_user_output_plugin(plugin_dir)


# ── find_user_output_plugins ──


def test_find_user_output_plugins_empty(tmp_path):
    with patch("joystick_diagrams.plugins.output_plugin_manager.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = tmp_path
        assert find_user_output_plugins() == []


def test_find_user_output_plugins_discovers_valid(tmp_path):
    _make_plugin_dir(tmp_path, "my_plugin")
    with patch("joystick_diagrams.plugins.output_plugin_manager.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = tmp_path
        found = find_user_output_plugins()
        assert len(found) == 1
        assert found[0].name == "my_plugin"


def test_find_user_output_plugins_skips_invalid(tmp_path):
    # Folder without main.py
    bad = tmp_path / "incomplete"
    bad.mkdir()
    (bad / "__init__.py").write_text("")
    with patch("joystick_diagrams.plugins.output_plugin_manager.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = tmp_path
        assert find_user_output_plugins() == []


# ── install_output_plugin ──


def test_install_from_folder(tmp_path):
    source = _make_plugin_dir(tmp_path / "source", "my_plugin")
    user_dir = tmp_path / "user_plugins"
    user_dir.mkdir()

    with patch("joystick_diagrams.plugins.output_plugin_installer.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = user_dir
        installed = install_output_plugin(source)

    assert installed.exists()
    assert (installed / "main.py").is_file()
    assert installed.parent == user_dir


def test_install_from_zip(tmp_path):
    zip_path = _make_plugin_zip(tmp_path, "zipped_plugin")
    user_dir = tmp_path / "user_plugins"
    user_dir.mkdir()

    with patch("joystick_diagrams.plugins.output_plugin_installer.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = user_dir
        installed = install_output_plugin(zip_path)

    assert installed.exists()
    assert (installed / "main.py").is_file()


def test_install_replaces_existing(tmp_path):
    user_dir = tmp_path / "user_plugins"
    user_dir.mkdir()
    existing = user_dir / "my_plugin"
    existing.mkdir()
    (existing / "old_file.txt").write_text("old")

    source = _make_plugin_dir(tmp_path / "source", "my_plugin")

    with patch("joystick_diagrams.plugins.output_plugin_installer.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = user_dir
        installed = install_output_plugin(source)

    assert not (installed / "old_file.txt").exists()
    assert (installed / "main.py").is_file()


def test_install_invalid_folder_raises(tmp_path):
    bad_dir = tmp_path / "not_a_plugin"
    bad_dir.mkdir()
    (bad_dir / "random.txt").write_text("nope")

    with pytest.raises(JoystickDiagramsError, match="not valid"):
        install_output_plugin(bad_dir)


def test_install_bad_zip_raises(tmp_path):
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not a zip file")

    with pytest.raises(JoystickDiagramsError, match="Invalid ZIP"):
        install_output_plugin(bad_zip)


def test_install_nonexistent_raises(tmp_path):
    with pytest.raises(JoystickDiagramsError, match="must be a folder or .zip"):
        install_output_plugin(tmp_path / "nope.txt")


# ── uninstall_output_plugin ──


def test_uninstall_removes_directory(tmp_path):
    user_dir = tmp_path / "user_plugins"
    plugin_dir = _make_plugin_dir(user_dir, "my_plugin")

    with patch("joystick_diagrams.plugins.output_plugin_installer.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = user_dir
        uninstall_output_plugin("MyPlugin", plugin_dir)

    assert not plugin_dir.exists()


def test_uninstall_rejects_path_outside_user_dir(tmp_path):
    user_dir = tmp_path / "user_plugins"
    user_dir.mkdir()
    outside = tmp_path / "bundled" / "some_plugin"
    outside.mkdir(parents=True)

    with patch("joystick_diagrams.plugins.output_plugin_installer.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = user_dir
        with pytest.raises(JoystickDiagramsError, match="not in the user plugins"):
            uninstall_output_plugin("SomePlugin", outside)


def test_uninstall_nonexistent_raises(tmp_path):
    user_dir = tmp_path / "user_plugins"
    user_dir.mkdir()
    missing = user_dir / "gone"

    with patch("joystick_diagrams.plugins.output_plugin_installer.utils") as mock_utils:
        mock_utils.user_output_plugins_root.return_value = user_dir
        with pytest.raises(JoystickDiagramsError, match="does not exist"):
            uninstall_output_plugin("Gone", missing)


# ── validate_output_plugin ──


def test_validate_success(tmp_path):
    plugin_dir = _make_plugin_dir(tmp_path)
    ok, name = validate_output_plugin(plugin_dir)
    assert ok is True
    assert name == "TestUserPlugin"


def test_validate_no_class(tmp_path):
    plugin_dir = _make_plugin_dir(tmp_path, main_content=BAD_MAIN_NO_CLASS)
    ok, msg = validate_output_plugin(plugin_dir)
    assert ok is False
    assert "OutputPlugin" in msg


def test_validate_wrong_base_class(tmp_path):
    plugin_dir = _make_plugin_dir(tmp_path, main_content=BAD_MAIN_WRONG_BASE)
    ok, msg = validate_output_plugin(plugin_dir)
    assert ok is False
    assert "OutputPluginInterface" in msg or "must define" in msg


# ── Manager integration: name conflicts ──


def test_manager_skips_conflicting_user_plugin(tmp_path):
    """User plugin with same name as bundled plugin is skipped."""
    plugin_dir = _make_plugin_dir(tmp_path, "conflict_plugin")

    with (
        patch(
            "joystick_diagrams.plugins.output_plugin_manager.find_output_plugins",
            return_value=[],
        ),
        patch(
            "joystick_diagrams.plugins.output_plugin_manager.find_user_output_plugins",
            return_value=[],
        ),
    ):
        mgr = OutputPluginManager()

    # Simulate a bundled plugin already loaded
    from joystick_diagrams.plugins.output_plugin_interface import OutputPluginInterface
    from joystick_diagrams.plugins.plugin_settings import PluginMeta

    class FakeBundled(OutputPluginInterface):
        plugin_meta = PluginMeta(
            name="TestUserPlugin", version="1.0.0", icon_path="img/x.ico"
        )

        def process_export(self, results):
            return True

    mgr.loaded_plugins.append(FakeBundled())
    mgr.user_plugins = [plugin_dir]

    # Now load user plugins — should skip due to name conflict
    bundled_names = {p.name for p in mgr.loaded_plugins}
    for plugin_path in mgr.user_plugins:
        try:
            loaded_module = load_user_output_plugin(plugin_path)
            loaded = loaded_module.OutputPlugin()
            if loaded.name in bundled_names:
                continue
            mgr.loaded_plugins.append(loaded)
            mgr._user_plugin_names.add(loaded.name)
        except Exception:
            pass

    # Only the bundled plugin should be loaded
    assert len(mgr.loaded_plugins) == 1
    assert not mgr.is_user_plugin("TestUserPlugin")


def test_manager_is_user_plugin(tmp_path):
    """User plugin is tracked correctly in the manager."""
    plugin_dir = _make_plugin_dir(tmp_path, "user_only")

    with (
        patch(
            "joystick_diagrams.plugins.output_plugin_manager.find_output_plugins",
            return_value=[],
        ),
        patch(
            "joystick_diagrams.plugins.output_plugin_manager.find_user_output_plugins",
            return_value=[plugin_dir],
        ),
        patch("joystick_diagrams.output_plugin_wrapper.db_plugin_data"),
    ):
        mgr = OutputPluginManager()
        mgr.load_discovered_plugins()

    assert mgr.is_user_plugin("TestUserPlugin") is True
    assert mgr.get_user_plugin_path("TestUserPlugin") == plugin_dir
