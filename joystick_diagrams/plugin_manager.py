"""Plugin Manager for Joystick Diagrams.

Plugin manager serves as the main interface between the GUI and the rest of the application.

- It is responsible for loading and unloading plugins

"""
import logging
import os
import shutil
import zipfile
from importlib import import_module
from json import JSONDecodeError
from pathlib import Path
from typing import Union, final

from dynaconf import ValidationError

import joystick_diagrams.exceptions as JDException
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface

_logger = logging.getLogger(__name__)

PLUGINS_DIRECTORY: str = "plugins"
PLUGIN_REL_PATH: str = ".plugins."
EXPECTED_PLUGIN_FILES = ["__init__.py", "config.py", "main.py", "settings.json"]
EXCLUDED_PLUGIN_DIRS = ["__pycache__"]


class ParserPluginManager:
    def __init__(self) -> None:
        self.plugins: list[Path] = find_plugins(PLUGINS_DIRECTORY)
        self.loaded_plugins: list[PluginInterface] = []

        if self.plugins:
            for plugin in self.plugins:
                try:
                    _logger.debug(f"Loading plugin {plugin}")
                    # Try initiate the plugin
                    loaded = load_plugin(plugin_package_name=plugin.name)
                    self.validate_plugin_settings(loaded)
                    self.loaded_plugins.append(loaded)

                except (JDException.PluginNotValid, JSONDecodeError, AttributeError, ValidationError) as e:
                    _logger.error(f"Error with Plugin: {plugin} - {e}")

        else:
            _logger.error("No valid plugins exist to load")
            # raise JDException.NoPluginsExist()

    def validate_plugin_settings(self, plugin: PluginInterface) -> None | ValidationError:
        return plugin.settings.validators.validate_all()

    def get_available_plugins(self) -> list[PluginInterface]:
        return [x for x in self.loaded_plugins]

    def install_plugin(self, plugin_package: Path):
        if not isinstance(plugin_package, Path):
            raise TypeError("Plugin path must be a valid path object")

        # Support for ZIP files
        if plugin_package.is_file() and plugin_package.suffix == ".zip":
            _logger.info(f"Trying to unpack ZIP plugin: {plugin_package}")
            unpacked_zip = self.handle_zip_plugin(plugin_package)

            check = check_folder_validity(unpacked_zip)

            try:
                _move = shutil.move(
                    unpacked_zip, Path(os.path.join(Path(__file__).resolve().parent, PLUGINS_DIRECTORY))
                )
                _logger.info(f"Unzipped plugin installed to: {_move}")
            except shutil.Error as e:
                raise JDException.JoystickDiagramsException(
                    f"Error when installing plugin in target directory: {e}"
                ) from e  # Move to new Exception Type
            finally:
                self.clean_plugin_unpack_directory(unpacked_zip)

        # Support for folder
        if plugin_package.is_dir():
            check = check_folder_validity(plugin_package)

            try:
                _move = shutil.copy(
                    unpacked_zip, Path(os.path.join(Path(__file__).resolve().parent, PLUGINS_DIRECTORY))
                )
                _logger.info(f"Unzipped plugin installed to: {_move}")
            except shutil.Error as e:
                raise JDException.JoystickDiagramsException(
                    f"Error when installing plugin in target directory: {e}"
                ) from e  # Move to new Exception Type

        # TODO POST STEPS / Initialisation / Hotload / Signing

    def handle_zip_plugin(self, zip_file: Path):
        # unpack zip
        zip = zipfile.ZipFile(zip_file, mode="r")
        extract_path = Path.joinpath(Path.cwd(), Path("temp"))

        # Check zip integrity
        try:
            zip.testzip()
        except zipfile.BadZipFile as e:
            _logger.warning(f"Zip file was loaded from {zip_file} but invalid")
            raise JDException.JoystickDiagramsException(
                "Plugin zip file not valid"
            ) from e  # Move to new Exception Type

        # Extract the ZIP
        zip.extractall(extract_path)

        # Get the folder unpacked from the ZIP
        items = os.listdir(extract_path)

        if not len(items) == 1:
            raise JDException.JoystickDiagramsException(
                "Plugin zip file not valid, more than one item unpacked from zip."
            )

        unpacked_item = Path.joinpath(extract_path, items[0])

        if not unpacked_item.is_dir():
            raise JDException.JoystickDiagramsException("Plugin zip file not valid, item unpacked is not a directory")

        return Path.joinpath(extract_path, items[0])

    def clean_plugin_unpack_directory(self, directory: Path):
        _logger.info("Attempting to remove unpack directory for plugin at {directory}")
        if directory.is_dir():
            shutil.rmtree(directory)

    def verify_plugin_signature(self) -> bool:
        "Used to verify a package for official Author."
        return True

    def process_loaded_plugins(self) -> list[Union[str, ProfileCollection]]:
        processed_plugin_data = []
        for plugin in self.loaded_plugins:
            # TODO path is not proper way to check, add in some way of knowing if a plugin has been initialised i.e. path set/instance created
            if plugin.path:
                if plugin.instance:  # TODO needs to go into main pattern for plugin
                    processed_plugin_data.append([plugin.name, plugin.process()])

        return processed_plugin_data


def load_plugin(plugin_package_directory: str = PLUGIN_REL_PATH, plugin_package_name: str = "") -> PluginInterface:
    """Attempt to load the plugin"""
    try:
        _logger.debug(f"Loading plugin at module path: {plugin_package_name}")
        return import_module(
            f"{plugin_package_directory}{plugin_package_name}.main", package="joystick_diagrams"
        ).ParserPlugin()
    except TypeError as e:
        _logger.error(f"{e} - {plugin_package_name}")
        raise JDException.PluginNotValid(error=e, value=plugin_package_name) from e
    except ModuleNotFoundError as e:
        _logger.error(e)
        raise JDException.PluginNotValid(value=plugin_package_name, error=e) from e


def find_plugins(directory) -> list[Path]:
    """Find python modules in given directory.

    Returns list of Paths with valid plugins contained within them.

    """
    _folders = [folder for folder in Path(os.path.join(Path(__file__).resolve().parent, directory)).iterdir()]
    _logger.debug(f"CWD for __file__ resolve: {Path(__file__).resolve()}")
    _logger.debug(f"Folders detected: {_folders}")

    folders = [
        folder for folder in _folders if check_folder_validity(folder) and folder.name not in EXCLUDED_PLUGIN_DIRS
    ]

    _logger.debug(f"Valid Plugins were detected: {folders}")
    return folders


def check_expected_files(directory: Path):
    return True
    directory_files = [f.name for f in directory.iterdir() if f.is_file()]

    for _file in EXPECTED_PLUGIN_FILES:
        if _file not in directory_files:
            return False

    return True


def check_folder_validity(folder: Path):
    if folder.is_dir() and check_expected_files(folder):
        return True

    return False


if __name__ == "__main__":
    app = ParserPluginManager()

    app.install_plugin(Path("D:\\Git Repos\\joystick-diagrams\\_DISABLED\\dcs_world_plugin_other.zip"))
