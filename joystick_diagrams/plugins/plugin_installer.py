"""Unified plugin installer for parser and output plugins.

Handles installation from local paths (ZIP/folder) and URLs,
uninstallation, and post-install validation for both plugin types.
"""

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Literal

import requests

from joystick_diagrams import utils
from joystick_diagrams.exceptions import JoystickDiagramsError

_logger = logging.getLogger(__name__)

PluginType = Literal["parser", "output"]

EXPECTED_PLUGIN_FILES: list[str] = ["__init__", "main"]


def install_plugin(source: Path | str, plugin_type: PluginType) -> Path:
    """Install a plugin from a folder, ZIP file, or URL.

    Returns the installed plugin directory path.
    Raises JoystickDiagramsError on failure.
    """
    if isinstance(source, str) and (
        source.startswith("http://") or source.startswith("https://")
    ):
        return _install_from_url(source, plugin_type)

    source = Path(source)

    if source.is_file() and source.suffix == ".zip":
        return _install_from_zip(source, plugin_type)
    elif source.is_dir():
        return _install_from_folder(source, plugin_type)
    else:
        raise JoystickDiagramsError(
            f"Plugin source must be a folder, .zip file, or URL: {source}"
        )


def uninstall_plugin(
    plugin_name: str, plugin_path: Path, plugin_type: PluginType
) -> None:
    """Remove a user-installed plugin.

    Only removes from the user plugins directory for the given type.
    """
    user_root = _get_user_root(plugin_type)

    try:
        plugin_path.resolve().relative_to(user_root.resolve())
    except ValueError as e:
        raise JoystickDiagramsError(
            f"Cannot uninstall plugin '{plugin_name}': "
            f"path {plugin_path} is not in the user {plugin_type} plugins directory."
        ) from e

    if plugin_path.is_dir():
        shutil.rmtree(plugin_path)
        _logger.info(
            f"Uninstalled user {plugin_type} plugin '{plugin_name}' from {plugin_path}"
        )
    else:
        raise JoystickDiagramsError(f"Plugin directory does not exist: {plugin_path}")


def validate_plugin(plugin_path: Path, plugin_type: PluginType) -> tuple[bool, str]:
    """Validate that a plugin directory contains a loadable plugin of the given type.

    Returns (True, plugin_name) on success, (False, error_message) on failure.
    """
    if plugin_type == "parser":
        return _validate_parser_plugin(plugin_path)
    else:
        return _validate_output_plugin(plugin_path)


def check_folder_validity(folder: Path) -> bool:
    """Check that a folder contains the required plugin files (__init__.py and main.py)."""
    if not folder.is_dir():
        return False
    directory_files = {f.stem for f in folder.iterdir() if f.is_file()}
    return all(f in directory_files for f in EXPECTED_PLUGIN_FILES)


def _get_user_root(plugin_type: PluginType) -> Path:
    if plugin_type == "parser":
        return utils.user_parser_plugins_root()
    else:
        return utils.user_output_plugins_root()


def _install_from_folder(folder: Path, plugin_type: PluginType) -> Path:
    if not check_folder_validity(folder):
        raise JoystickDiagramsError(
            f"Plugin folder '{folder.name}' is not valid. "
            f"It must contain __init__.py and main.py."
        )

    dest = Path.joinpath(_get_user_root(plugin_type), folder.name)
    if dest.exists():
        _logger.info(f"Replacing existing user plugin at {dest}")
        shutil.rmtree(dest)

    shutil.copytree(folder, dest)
    _logger.info(f"{plugin_type.capitalize()} plugin installed to {dest}")
    return dest


def _install_from_zip(zip_path: Path, plugin_type: PluginType) -> Path:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.testzip()
    except zipfile.BadZipFile as e:
        raise JoystickDiagramsError(f"Invalid ZIP file: {zip_path}") from e

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)

        items = [i for i in tmp_path.iterdir() if i.is_dir()]
        if len(items) != 1:
            raise JoystickDiagramsError(
                "Plugin ZIP must contain exactly one top-level directory."
            )

        extracted = items[0]
        if not check_folder_validity(extracted):
            raise JoystickDiagramsError(
                f"Extracted plugin '{extracted.name}' is not valid. "
                f"It must contain __init__.py and main.py."
            )

        return _install_from_folder(extracted, plugin_type)


def _install_from_url(url: str, plugin_type: PluginType) -> Path:
    """Download a plugin ZIP from a URL and install it."""
    _logger.info(f"Downloading plugin from {url}")

    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        raise JoystickDiagramsError(f"Failed to download plugin: {e}") from e

    content_type = response.headers.get("content-type", "")
    if not url.lower().endswith(".zip") and "zip" not in content_type.lower():
        raise JoystickDiagramsError(
            "URL does not appear to point to a ZIP file. "
            "The URL should end in .zip or serve a ZIP content type."
        )

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "plugin.zip"
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return _install_from_zip(zip_path, plugin_type)


def _validate_parser_plugin(plugin_path: Path) -> tuple[bool, str]:
    from joystick_diagrams.plugins.plugin_interface import PluginInterface
    from joystick_diagrams.plugins.plugin_manager import load_user_parser_plugin

    try:
        module = load_user_parser_plugin(plugin_path)
    except Exception as e:
        return False, f"Failed to load plugin module: {e}"

    if not hasattr(module, "ParserPlugin"):
        return False, "main.py does not define a 'ParserPlugin' class."

    try:
        instance = module.ParserPlugin()
    except Exception as e:
        return False, f"Failed to instantiate ParserPlugin: {e}"

    if not isinstance(instance, PluginInterface):
        return False, "ParserPlugin does not inherit from PluginInterface."

    return True, instance.name


def _validate_output_plugin(plugin_path: Path) -> tuple[bool, str]:
    from joystick_diagrams.plugins.output_plugin_interface import OutputPluginInterface
    from joystick_diagrams.plugins.output_plugin_manager import load_user_output_plugin

    try:
        module = load_user_output_plugin(plugin_path)
    except Exception as e:
        return False, f"Failed to load plugin module: {e}"

    if not hasattr(module, "OutputPlugin"):
        return False, "main.py does not define an 'OutputPlugin' class."

    try:
        instance = module.OutputPlugin()
    except Exception as e:
        return False, f"Failed to instantiate OutputPlugin: {e}"

    if not isinstance(instance, OutputPluginInterface):
        return False, "OutputPlugin does not inherit from OutputPluginInterface."

    return True, instance.name
