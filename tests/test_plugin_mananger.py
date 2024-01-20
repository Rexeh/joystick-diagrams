import pytest

from joystick_diagrams import exceptions, plugin_manager
from joystick_diagrams.plugin_manager import load_plugin

TEST_PLUGIN_PATH = "../tests/data/test_plugins"


def test_instance_creation():
    plugin_manager.PLUGIN_REL_PATH = "tests.data.test_plugins."
    plugin_manager.PLUGINS_DIRECTORY = TEST_PLUGIN_PATH

    inst = plugin_manager.ParserPluginManager()

    assert isinstance(inst, plugin_manager.ParserPluginManager)
    assert len(inst.loaded_plugins) > 0
    assert len(inst.plugins) > 0


def test_find_plugins():
    plugins = plugin_manager.find_plugins(TEST_PLUGIN_PATH)

    assert len(plugins) == 1
    assert plugins[0].name == "examplePlugin"


# Test when the plugin is loaded successfully
def test_load_plugin_success():
    # Call the function with a test plugin_package and module_path
    plugin_package = "tests.data.test_plugins."
    module_path = "examplePlugin"
    result = load_plugin(plugin_package, module_path)

    # Assert that the result is the instance of ParserPlugin
    assert "examplePlugin" in result.icon
    assert result.name == "test plugin"
    assert result.version == "1.0.5"


# Test when the plugin is loaded successfully
def test_load_plugin_not_valid(caplog):
    # Call the function with a test plugin_package and module_path
    plugin_package = "tests.data.test_plugins."
    module_path = "notPlugin"

    with pytest.raises(exceptions.PluginNotValid) as e:
        load_plugin(plugin_package, module_path)

    assert "notPlugin.main" in caplog.text
