from joystick_diagrams.app_state import appState
from joystick_diagrams.plugin_manager import ParserPluginManager

# Get global state object
_state = appState()

# Initialise Plugins System
plugins = ParserPluginManager()
_state.init_plugins(plugins)
