"""Tests for SHA-256 integrity verification in the plugin installer."""

import hashlib
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.plugins.plugin_installer import install_plugin

MAIN = "# minimal plugin main\n"


def _make_plugin_zip(base: Path, name: str = "sha_plugin") -> Path:
    src = base / "src" / name
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "main.py").write_text(MAIN)
    zip_path = base / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in src.iterdir():
            zf.write(f, f"{name}/{f.name}")
    return zip_path


def test_install_zip_with_matching_sha256_succeeds(tmp_path):
    zip_path = _make_plugin_zip(tmp_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    user_dir = tmp_path / "user"
    user_dir.mkdir()

    with patch("joystick_diagrams.plugins.plugin_installer.utils") as mock_utils:
        mock_utils.user_parser_plugins_root.return_value = user_dir
        installed = install_plugin(zip_path, "parser", expected_sha256=digest)

    assert installed.exists()
    assert (installed / "main.py").is_file()


def test_install_zip_with_mismatched_sha256_aborts(tmp_path):
    zip_path = _make_plugin_zip(tmp_path)
    user_dir = tmp_path / "user"
    user_dir.mkdir()

    with patch("joystick_diagrams.plugins.plugin_installer.utils") as mock_utils:
        mock_utils.user_parser_plugins_root.return_value = user_dir
        with pytest.raises(JoystickDiagramsError, match="integrity check"):
            install_plugin(zip_path, "parser", expected_sha256="0" * 64)

    # Nothing should have been installed into the user directory.
    assert list(user_dir.iterdir()) == []


def test_install_zip_sha256_is_case_insensitive(tmp_path):
    zip_path = _make_plugin_zip(tmp_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest().upper()
    user_dir = tmp_path / "user"
    user_dir.mkdir()

    with patch("joystick_diagrams.plugins.plugin_installer.utils") as mock_utils:
        mock_utils.user_parser_plugins_root.return_value = user_dir
        installed = install_plugin(zip_path, "parser", expected_sha256=digest)

    assert installed.exists()
