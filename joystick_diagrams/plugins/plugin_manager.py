"""Plugin Manager for Joystick Diagrams.

Plugin manager serves as the main interface between the GUI and the rest of the application.

- It is responsible for loading and unloading plugins

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
from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.plugins.plugin_interface import PluginInterface

_logger = logging.getLogger(__name__)

PLUGINS_DIRECTORY: str = "."
PLUGIN_REL_PATH: str = ".plugins."
EXPECTED_PLUGIN_FILES: list[str] = ["__init__", "main"]
EXCLUDED_PLUGIN_DIRS: list[str] = ["__pycache__"]


class ParserPluginManager:
    def __init__(self) -> None:
        self.plugins: list[Path] = find_plugins(PLUGINS_DIRECTORY)
        self.user_plugins: list[Path] = find_user_parser_plugins()
        self.loaded_plugins: list[PluginInterface] = []
        self.plugin_wrappers: list[PluginWrapper] = []
        self._user_plugin_names: set[str] = set()
        self._user_plugin_paths: dict[str, Path] = {}
        self.conflicts: list[tuple[str, Path]] = []

    def create_plugin_wrappers(self):
        for plugin in self.get_available_plugins():
            self.plugin_wrappers.append(PluginWrapper(plugin))

    def execute_plugin_wrapper_process(self, plugin_wrapper: PluginWrapper):
        """Executes a plugin wrapper if it in a ready state"""

        if plugin_wrapper.ready:
            plugin_wrapper.process()

    def get_enabled_plugin_wrappers(self):
        "Returns plugin wrappers where the plugin is enabled"
        return [x for x in self.plugin_wrappers if x.enabled is True]

    def load_discovered_plugins(self) -> None:
        """Load and validate the plugins that were found during iniitalisation.

        - Loads a plugin using importlib
        - Validates the plugin with further checks
        """
        if not self.plugins and not self.user_plugins:
            _logger.error("No valid plugins exist to load")
            return

        # Load bundled plugins
        for plugin in self.plugins:
            try:
                _logger.debug(f"Loading plugin {plugin}")
                loaded_module = load_plugin(plugin_package_name=plugin.name)
                loaded = loaded_module.ParserPlugin()
                self.loaded_plugins.append(loaded)
            except (
                JoystickDiagramsError,
                JSONDecodeError,
                AttributeError,
                TypeError,
            ) as e:
                _logger.error(f"Error with Plugin: {plugin} - {e}")

        # Load user-installed plugins
        bundled_names = {p.name for p in self.loaded_plugins}
        for plugin_path in self.user_plugins:
            try:
                _logger.debug(f"Loading user parser plugin {plugin_path}")
                loaded_module = load_user_parser_plugin(plugin_path)
                loaded = loaded_module.ParserPlugin()

                if loaded.name in bundled_names:
                    _logger.warning(
                        f"User plugin '{loaded.name}' conflicts with bundled plugin "
                        f"of same name. Skipping user plugin at {plugin_path}."
                    )
                    self.conflicts.append((loaded.name, plugin_path))
                    continue

                self.loaded_plugins.append(loaded)
                self._user_plugin_names.add(loaded.name)
                self._user_plugin_paths[loaded.name] = plugin_path
            except Exception as e:
                _logger.error(f"Error loading user parser plugin: {plugin_path} - {e}")

    def get_available_plugins(self) -> list[PluginInterface]:
        return [x for x in self.loaded_plugins]

    def is_user_plugin(self, name: str) -> bool:
        return name in self._user_plugin_names

    def get_user_plugin_path(self, name: str) -> Path | None:
        return self._user_plugin_paths.get(name)


def find_user_parser_plugins() -> list[Path]:
    """Discover user-installed parser plugins from the user data directory."""
    user_dir = utils.user_parser_plugins_root()
    if not user_dir.is_dir():
        return []

    folders = [
        folder
        for folder in user_dir.iterdir()
        if check_folder_validity(folder) and folder.name not in EXCLUDED_PLUGIN_DIRS
    ]
    _logger.debug(f"Valid user parser plugins detected: {folders}")
    return folders


def load_user_parser_plugin(plugin_path: Path) -> ModuleType:
    """Load a parser plugin from an arbitrary filesystem path.

    Uses spec_from_file_location so plugins outside the joystick_diagrams
    package can be loaded. Works in frozen (cx_freeze) environments.
    """
    main_file = Path.joinpath(plugin_path, "main.py")
    if not main_file.is_file():
        raise PluginNotValidError(
            value=str(plugin_path),
            error="Plugin directory does not contain main.py",
        )

    module_name = f"jd_user_parser_plugin_{plugin_path.name}"
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


def load_plugin(
    plugin_package_directory: str = PLUGIN_REL_PATH, plugin_package_name: str = ""
) -> ModuleType:
    """Loads a plugin module at a given package directory"""
    try:
        _logger.debug(f"Loading plugin at module path: {plugin_package_name}")
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


def find_plugins(directory) -> list[Path]:
    """Find python modules in given directory.

    Returns list of Paths with valid plugins contained within them.

    """
    _folders = [
        folder
        for folder in Path(
            os.path.join(Path(__file__).resolve().parent, directory)
        ).iterdir()
    ]
    _logger.debug(f"CWD for __file__ resolve: {Path(__file__).resolve()}")
    _logger.debug(f"Folders detected: {_folders}")

    folders = [
        folder
        for folder in _folders
        if check_folder_validity(folder) and folder.name not in EXCLUDED_PLUGIN_DIRS
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
