"""Install and uninstall user output plugins."""

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from joystick_diagrams import utils
from joystick_diagrams.exceptions import JoystickDiagramsError
from joystick_diagrams.plugins.output_plugin_manager import _check_folder_validity

_logger = logging.getLogger(__name__)


def install_output_plugin(source: Path) -> Path:
    """Install an output plugin from a folder or ZIP file.

    Returns the installed plugin directory path.
    Raises JoystickDiagramsError on validation failure.
    """
    if source.is_file() and source.suffix == ".zip":
        return _install_from_zip(source)
    elif source.is_dir():
        return _install_from_folder(source)
    else:
        raise JoystickDiagramsError(
            f"Plugin source must be a folder or .zip file: {source}"
        )


def _install_from_folder(folder: Path) -> Path:
    if not _check_folder_validity(folder):
        raise JoystickDiagramsError(
            f"Plugin folder '{folder.name}' is not valid. "
            f"It must contain __init__.py and main.py."
        )

    dest = Path.joinpath(utils.user_output_plugins_root(), folder.name)
    if dest.exists():
        _logger.info(f"Replacing existing user plugin at {dest}")
        shutil.rmtree(dest)

    shutil.copytree(folder, dest)
    _logger.info(f"Output plugin installed to {dest}")
    return dest


def _install_from_zip(zip_path: Path) -> Path:
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
        if not _check_folder_validity(extracted):
            raise JoystickDiagramsError(
                f"Extracted plugin '{extracted.name}' is not valid. "
                f"It must contain __init__.py and main.py."
            )

        return _install_from_folder(extracted)


def uninstall_output_plugin(plugin_name: str, plugin_path: Path) -> None:
    """Remove a user-installed output plugin.

    Only removes from the user output_plugins directory.
    """
    user_root = utils.user_output_plugins_root()

    try:
        plugin_path.resolve().relative_to(user_root.resolve())
    except ValueError as e:
        raise JoystickDiagramsError(
            f"Cannot uninstall plugin '{plugin_name}': "
            f"path {plugin_path} is not in the user plugins directory."
        ) from e

    if plugin_path.is_dir():
        shutil.rmtree(plugin_path)
        _logger.info(
            f"Uninstalled user output plugin '{plugin_name}' from {plugin_path}"
        )
    else:
        raise JoystickDiagramsError(f"Plugin directory does not exist: {plugin_path}")


def validate_output_plugin(plugin_path: Path) -> tuple[bool, str]:
    """Validate that a plugin directory contains a loadable OutputPlugin.

    Returns (True, plugin_name) on success, (False, error_message) on failure.
    """
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
