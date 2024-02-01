import unittest

import joystick_diagrams.plugins.dcs_world_plugin.dcs_world as dcs
from joystick_diagrams.input.axis import Axis
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat


class TestDCSParseTest(unittest.TestCase):
    def setUp(self):
        self.dcs_instance = dcs.DCSWorldParser("./tests/data/dcs_world/valid_dcs_world_directory")

    def test_no_profiles_parsed(self):
        pass

    def test_button_convert_button(self):
        button = self.dcs_instance.convert_button_format("JOY_BTN2")
        self.assertIsInstance(button, Button)

    def test_button_convert_axis(self):
        button = self.dcs_instance.convert_button_format("JOY_RZ")
        self.assertIsInstance(button, Axis)

        button = self.dcs_instance.convert_button_format("JOY_Z")
        self.assertIsInstance(button, Axis)

    def test_button_convert_pov(self):
        button = self.dcs_instance.convert_button_format("JOY_BTN_POV1_UR")
        self.assertIsInstance(button, Hat)

        button = self.dcs_instance.convert_button_format("JOY_BTN_POV2_UR")
        self.assertIsInstance(button, Hat)


if __name__ == "__main__":
    unittest.main()
