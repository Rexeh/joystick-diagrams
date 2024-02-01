import pytest

from joystick_diagrams import exceptions, plugin_manager
from joystick_diagrams.plugin_manager import load_plugin

TEST_PLUGIN_PATH = "../tests/data/test_plugins"


# Test when the plugin is loaded successfully
def test_load_plugin_not_valid(caplog):
    # Call the function with a test plugin_package and module_path
    plugin_package = "tests.data.test_plugins."
    module_path = "notPlugin"

    with pytest.raises(exceptions.PluginNotValid) as e:
        load_plugin(plugin_package, module_path)

    assert "notPlugin.main" in caplog.text
