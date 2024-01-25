from joystick_diagrams.app_state import AppState
from joystick_diagrams.plugin_manager import ParserPluginManager


def init():
    # Get global state object
    _state = AppState()

    # Initialise Plugins System
    plugins = ParserPluginManager()
    _state.init_plugins(plugins)


if __name__ == "__main__":
    pass
