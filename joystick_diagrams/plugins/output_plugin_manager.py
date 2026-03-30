"""Output Plugin Manager for Joystick Diagrams.

Discovers and loads post-processing output plugins from the output_plugins/ subdirectory.
"""

import logging
import os
from importlib import import_module
from json import JSONDecodeError
from pathlib import Path
from types import ModuleType

from joystick_diagrams.exceptions import JoystickDiagramsError, PluginNotValidError
from joystick_diagrams.output_plugin_wrapper import OutputPluginWrapper
from joystick_diagrams.plugins.output_plugin_interface import OutputPluginInterface

_logger = logging.getLogger(__name__)

OUTPUT_PLUGINS_DIRECTORY: str = "output_plugins"
OUTPUT_PLUGIN_REL_PATH: str = ".plugins.output_plugins."
EXPECTED_PLUGIN_FILES: list[str] = ["__init__", "main"]
EXCLUDED_PLUGIN_DIRS: list[str] = ["__pycache__"]


class OutputPluginManager:
    def __init__(self) -> None:
        self.plugins: list[Path] = find_output_plugins()
        self.loaded_plugins: list[OutputPluginInterface] = []
        self.plugin_wrappers: list[OutputPluginWrapper] = []

    def load_discovered_plugins(self) -> None:
        if not self.plugins:
            _logger.debug("No output plugins found to load")
            return

        for plugin in self.plugins:
            try:
                _logger.debug(f"Loading output plugin {plugin}")
                loaded_module = load_output_plugin(plugin_package_name=plugin.name)
                loaded = loaded_module.OutputPlugin()
                self.loaded_plugins.append(loaded)
            except (
                JoystickDiagramsError,
                JSONDecodeError,
                AttributeError,
                TypeError,
            ) as e:
                _logger.error(f"Error loading output plugin: {plugin} - {e}")

    def create_plugin_wrappers(self) -> None:
        for plugin in self.loaded_plugins:
            self.plugin_wrappers.append(OutputPluginWrapper(plugin))

    def get_enabled_plugin_wrappers(self) -> list[OutputPluginWrapper]:
        return [x for x in self.plugin_wrappers if x.enabled]


def find_output_plugins() -> list[Path]:
    plugins_dir = Path(
        os.path.join(Path(__file__).resolve().parent, OUTPUT_PLUGINS_DIRECTORY)
    )
    if not plugins_dir.is_dir():
        return []

    folders = [
        folder
        for folder in plugins_dir.iterdir()
        if _check_folder_validity(folder) and folder.name not in EXCLUDED_PLUGIN_DIRS
    ]
    _logger.debug(f"Valid output plugins detected: {folders}")
    return folders


def load_output_plugin(
    plugin_package_directory: str = OUTPUT_PLUGIN_REL_PATH,
    plugin_package_name: str = "",
) -> ModuleType:
    try:
        _logger.debug(f"Loading output plugin at module path: {plugin_package_name}")
        return import_module(
            f"{plugin_package_directory}{plugin_package_name}.main",
            package="joystick_diagrams",
        )
    except TypeError as e:
        _logger.error(f"{e} - {plugin_package_name}")
        raise PluginNotValidError(error=e, value=plugin_package_name) from e
    except ModuleNotFoundError as e:
        _logger.error(e)
        raise PluginNotValidError(value=plugin_package_name, error=e) from e


def _check_folder_validity(folder: Path) -> bool:
    if not folder.is_dir():
        return False
    directory_files = {f.stem for f in folder.iterdir() if f.is_file()}
    return all(f in directory_files for f in EXPECTED_PLUGIN_FILES)
