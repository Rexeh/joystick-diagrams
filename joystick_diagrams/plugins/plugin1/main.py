from joystick_diagrams.plugins.plugin_interface import PluginInterface

NAME = "Star Citizen"
VERSION = "0.0.1"


class CustomPlugin(PluginInterface):
    def process(self, num1, num2):
        # Some prints to identify which plugin is been used
        print("This is my another plugin")
        print(f"Numbers are {num1} and {num2}")

    def init(self):
        print("Init plugin")

    def load(self):
        print("Load plugin")

    def name(self) -> str:
        return NAME

    def version(self) -> str:
        return VERSION
