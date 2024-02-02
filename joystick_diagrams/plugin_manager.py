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
from types import ModuleType
from typing import Union

from dynaconf import ValidationError

from joystick_diagrams.exceptions import JoystickDiagramsException, PluginNotValid
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface

_logger = logging.getLogger(__name__)

PLUGINS_DIRECTORY: str = "plugins"
PLUGIN_REL_PATH: str = ".plugins."
EXPECTED_PLUGIN_FILES = ["__init__", "config", "main", "settings"]
EXCLUDED_PLUGIN_DIRS = ["__pycache__"]


class ParserPluginManager:
    def __init__(self) -> None:
        self.plugins: list[Path] = find_plugins(PLUGINS_DIRECTORY)
        self.loaded_plugins: list[PluginInterface] = []

    def load_discovered_plugins(self) -> None:
        """Load and validate the plugins that were found during iniitalisation.

        - Loads a plugin using importlib
        - Validates the plugin with further checks
        """
        if not self.plugins:
            _logger.error("No valid plugins exist to load")  # raise JDException.NoPluginsExist()
            return

        for plugin in self.plugins:
            try:
                _logger.debug(f"Loading plugin {plugin}")

                # Try load the PLugin Package
                loaded_module = load_plugin(plugin_package_name=plugin.name)

                # Try to instanciate the Plugin TODO add further checks
                loaded = loaded_module.ParserPlugin()

                self.validate_plugin_settings(loaded)
                self.loaded_plugins.append(loaded)

            except (JoystickDiagramsException, JSONDecodeError, AttributeError, ValidationError) as e:
                _logger.error(f"Error with Plugin: {plugin} - {e}")

    def validate_plugin_settings(self, plugin: PluginInterface) -> None | ValidationError:
        return plugin.settings.validators.validate_all()

    def get_available_plugins(self) -> list[PluginInterface]:
        return [x for x in self.loaded_plugins]

    def process_loaded_plugins(self) -> list[Union[str, ProfileCollection]]:
        processed_plugin_data = []
        for plugin in self.loaded_plugins:
            # TODO path is not proper way to check, add in some way of knowing if a plugin has been initialised i.e. path set/instance created
            if plugin.path:
                if plugin.instance:  # TODO needs to go into main pattern for plugin
                    processed_plugin_data.append([plugin.name, plugin.process()])

        return processed_plugin_data


def install_plugin(plugin_package: Path):
    """Validates and installs a provided Folder/ZIP as a plugin"""
    if not isinstance(plugin_package, Path):
        raise TypeError("Plugin path must be a valid path object")

    # Support for ZIP files
    if plugin_package.is_file() and plugin_package.suffix == ".zip":
        install_zip_plugin(plugin_package)

    # Support for folder
    if plugin_package.is_dir():
        install_folder_plugin(plugin_package)

    # TODO POST STEPS / Initialisation / Hotload / Signing


def install_folder_plugin(plugin_path: Path):
    check = check_folder_validity(plugin_path)

    if not check:
        _logger.error("Plugin folder failed validation, so will not be installed")
        return

    try:
        _move = shutil.copy(plugin_path, Path(os.path.join(Path(__file__).resolve().parent, PLUGINS_DIRECTORY)))
        _logger.info(f"Plugin installed to: {_move}")
    except shutil.Error as e:
        raise JoystickDiagramsException(
            f"Error when installing plugin in target directory: {e}"
        ) from e  # Move to new Exception Type


def install_zip_plugin(plugin_path: Path):
    _logger.info(f"Trying to unpack ZIP plugin: {plugin_path}")

    try:
        unpacked_zip = handle_zip_plugin(plugin_path)
    except JoystickDiagramsException as e:
        _logger.error(e)
        return

    check = check_folder_validity(unpacked_zip)

    if not check:
        _logger.error("Unpacked ZIP failed validation, so will not be installed")
        clean_plugin_unpack_directory(unpacked_zip)
        return

    try:
        _move = shutil.move(unpacked_zip, Path(os.path.join(Path(__file__).resolve().parent, PLUGINS_DIRECTORY)))
        _logger.info(f"Unzipped plugin installed to: {_move}")
    except shutil.Error as e:
        raise JoystickDiagramsException(
            f"Error when installing plugin in target directory: {e}"
        ) from e  # Move to new Exception Type
    finally:
        clean_plugin_unpack_directory(unpacked_zip)


def handle_zip_plugin(zip_file: Path) -> Path:
    """Validates a ZIP file and unpacks it to a directory

    Returns Path to unpackaged ZIP is valid
    """
    # unpack zip
    zip_obj = zipfile.ZipFile(zip_file, mode="r")
    extract_path = Path.joinpath(Path.cwd(), Path("temp"))

    # Check zip integrity
    try:
        zip_obj.testzip()
    except zipfile.BadZipFile as e:
        _logger.warning(f"Zip file was loaded from {zip_file} but invalid")
        raise JoystickDiagramsException("Plugin zip file not valid") from e  # Move to new Exception Type

    # Extract the ZIP
    zip_obj.extractall(extract_path)

    # Get the folder unpacked from the ZIP
    items = os.listdir(extract_path)

    if not len(items) == 1:
        raise JoystickDiagramsException("Plugin zip file not valid, more than one item unpacked from zip.")

    unpacked_item = Path.joinpath(extract_path, items[0])

    if not unpacked_item.is_dir():
        raise JoystickDiagramsException("Plugin zip file not valid, item unpacked is not a directory")

    return Path.joinpath(extract_path, items[0])


def clean_plugin_unpack_directory(directory: Path):
    _logger.info("Attempting to remove unpack directory for plugin at {directory}")
    if directory.is_dir():
        shutil.rmtree(directory)


def verify_plugin_signature() -> bool:
    "Used to verify a package for official Author."
    return True


def load_plugin(plugin_package_directory: str = PLUGIN_REL_PATH, plugin_package_name: str = "") -> ModuleType:
    """Loads a plugin module at a given package directory"""
    try:
        _logger.debug(f"Loading plugin at module path: {plugin_package_name}")
        return import_module(f"{plugin_package_directory}{plugin_package_name}.main", package="joystick_diagrams")
    except TypeError as e:
        _logger.error(f"{e} - {plugin_package_name}")
        raise PluginNotValid(error=e, value=plugin_package_name) from e
    except ModuleNotFoundError as e:
        _logger.error(e)
        raise PluginNotValid(value=plugin_package_name, error=e) from e


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
    # Stem added to handle frozen pyc compilation - Now checks only filenames
    directory_files = {f.stem for f in directory.iterdir() if f.is_file()}

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

    install_plugin(Path("D:\\Git Repos\\joystick-diagrams\\_DISABLED\\dcs_world_plugin_other.zip"))
