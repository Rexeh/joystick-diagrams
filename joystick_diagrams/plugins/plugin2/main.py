import logging
from joystick_diagrams.plugins.plugin_interface import PluginInterface

_logger = logging.getLogger(__name__)


class CustomPlugin(PluginInterface):
    def process(self, num1, num2):
        # Some prints to identify which plugin is been used
        print("This is my yet another plugin")
        print(f"Numbers are {num1} and {num2}")

    def init(self):
        print("Init plugin")

    def name(self) -> str:
        return "DCS Parser"

    def version(self) -> str:
        return super().version
