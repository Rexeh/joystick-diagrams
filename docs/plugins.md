# Joystick Diagrams - Plugins

> [!CAUTION]
> All information here is subject to change during the course of 2.0 pre-release. If you want to build a plugin based off this, then please get in touch on Discord to work together.

## Parser Plugins
With version 2.0, Joystick Diagrams has moved to a plugin system to allow further games to be supported faster.

## Plugin Structure
-  plugins/ - Directory for plugins
   - *plugin name*
     - \__init\__.py
     - main.py
     - config.py

### Example Plugin

```python
import logging
from pathlib import Path

from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings

PLUGIN_NAME = "MyPlugin"
PLUGIN_ICON = "img/logo.ico"
VERSION = "0.0.1"

_logger = logging.getLogger("__name__")


class ParserPlugin(PluginInterface):
    def __init__(self):
        self.path = None
        self.settings = settings

    def process(self) -> ProfileCollection():
        ## Parse things into an ProfileCollection()
        ## Return ProfileCollection()
        return None

    def set_path(self, path: Path) -> bool:
        ## Entrance point for UI to inject path to Plugin from User Input
        self.path = path
        return True

    @property
    def name(self) -> str:
        return f"{PLUGIN_NAME}"

    @property
    def version(self) -> str:
        return f"{VERSION}"

    @property
    def icon(self) -> str:
        return f"{Path.joinpath(Path(__file__).parent,PLUGIN_ICON)}"

    @property
    def get_path(self) -> bool:
        return self.path

```

## Configuration Management
Parsers are responsible for their own configuration file, using the Dynatrace module to provide functionality.

Configuration is provided by plugins **config.py** and the chosen format is JSON for configuration store.

You can retrieve settings for your plugin using **settings.VARIABLE**, for further usage and validation see [Dynaconf Documentation](https://www.dynaconf.com/)

### Surfacing Configuration Management
This is handled by the main app for all plugins, allowing users to visually configure settings for your plugin.