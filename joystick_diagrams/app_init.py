import logging

from joystick_diagrams.app_state import AppState
from joystick_diagrams.db import db_init
from joystick_diagrams.plugin_manager import ParserPluginManager

_logger = logging.getLogger(__name__)


def init():
    # TODO log and orchestrate this better

    # Setup datastore
    db_init.init()
    # -------------------------------

    # Get global state object
    _state = AppState()
    # -------------------------------

    # -- Initialise Plugins System --
    plugins = ParserPluginManager()
    plugins.load_discovered_plugins()
    plugins.create_plugin_wrappers()
    _state.init_plugins(plugins)

    # -------------------------------


if __name__ == "__main__":
    pass
