"""Output Plugin Manager for Joystick Diagrams.

Discovers and loads post-processing output plugins from the output_plugins/ subdirectory.
"""

import importlib.util
import logging
import os
import sys
from importlib import import_module
from json import JSONDecodeError
from pathlib import Path
from types import ModuleType

from joystick_diagrams import utils
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
        self.user_plugins: list[Path] = find_user_output_plugins()
        self.loaded_plugins: list[OutputPluginInterface] = []
        self.plugin_wrappers: list[OutputPluginWrapper] = []
        self._user_plugin_names: set[str] = set()
        self._user_plugin_paths: dict[str, Path] = {}

    def load_discovered_plugins(self) -> None:
        # Load bundled plugins
        for plugin in self.plugins:
            try:
                _logger.debug(f"Loading bundled output plugin {plugin}")
                loaded_module = load_output_plugin(plugin_package_name=plugin.name)
                loaded = loaded_module.OutputPlugin()
                self.loaded_plugins.append(loaded)
            except (
                JoystickDiagramsError,
                JSONDecodeError,
                AttributeError,
                TypeError,
            ) as e:
                _logger.error(f"Error loading bundled output plugin: {plugin} - {e}")

        # Load user-installed plugins
        bundled_names = {p.name for p in self.loaded_plugins}
        for plugin_path in self.user_plugins:
            try:
                _logger.debug(f"Loading user output plugin {plugin_path}")
                loaded_module = load_user_output_plugin(plugin_path)
                loaded = loaded_module.OutputPlugin()

                if loaded.name in bundled_names:
                    _logger.warning(
                        f"User plugin '{loaded.name}' conflicts with bundled plugin "
                        f"of same name. Skipping user plugin at {plugin_path}."
                    )
                    continue

                self.loaded_plugins.append(loaded)
                self._user_plugin_names.add(loaded.name)
                self._user_plugin_paths[loaded.name] = plugin_path
            except Exception as e:
                _logger.error(f"Error loading user output plugin: {plugin_path} - {e}")

    def create_plugin_wrappers(self) -> None:
        for plugin in self.loaded_plugins:
            self.plugin_wrappers.append(OutputPluginWrapper(plugin))

    def get_enabled_plugin_wrappers(self) -> list[OutputPluginWrapper]:
        return [x for x in self.plugin_wrappers if x.enabled]

    def is_user_plugin(self, name: str) -> bool:
        return name in self._user_plugin_names

    def get_user_plugin_path(self, name: str) -> Path | None:
        return self._user_plugin_paths.get(name)


def find_user_output_plugins() -> list[Path]:
    """Discover user-installed output plugins from the user data directory."""
    user_dir = utils.user_output_plugins_root()
    if not user_dir.is_dir():
        return []

    folders = [
        folder
        for folder in user_dir.iterdir()
        if _check_folder_validity(folder) and folder.name not in EXCLUDED_PLUGIN_DIRS
    ]
    _logger.debug(f"Valid user output plugins detected: {folders}")
    return folders


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


def load_user_output_plugin(plugin_path: Path) -> ModuleType:
    """Load an output plugin from an arbitrary filesystem path.

    Uses spec_from_file_location so plugins outside the joystick_diagrams
    package can be loaded. Works in frozen (cx_freeze) environments.
    """
    main_file = Path.joinpath(plugin_path, "main.py")
    if not main_file.is_file():
        raise PluginNotValidError(
            value=str(plugin_path),
            error="Plugin directory does not contain main.py",
        )

    module_name = f"jd_user_output_plugin_{plugin_path.name}"
    spec = importlib.util.spec_from_file_location(
        f"{module_name}.main",
        str(main_file),
        submodule_search_locations=[str(plugin_path)],
    )
    if spec is None or spec.loader is None:
        raise PluginNotValidError(
            value=str(plugin_path),
            error="Could not create module spec for plugin",
        )

    # Register the parent package so relative imports within the plugin work
    if module_name not in sys.modules:
        parent_spec = importlib.util.spec_from_file_location(
            module_name,
            str(Path.joinpath(plugin_path, "__init__.py")),
            submodule_search_locations=[str(plugin_path)],
        )
        if parent_spec is not None:
            parent_module = importlib.util.module_from_spec(parent_spec)
            sys.modules[module_name] = parent_module
            if parent_spec.loader is not None:
                parent_spec.loader.exec_module(parent_module)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _check_folder_validity(folder: Path) -> bool:
    if not folder.is_dir():
        return False
    directory_files = {f.stem for f in folder.iterdir() if f.is_file()}
    return all(f in directory_files for f in EXPECTED_PLUGIN_FILES)
