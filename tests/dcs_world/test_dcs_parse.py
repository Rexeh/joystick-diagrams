import unittest

import joystick_diagrams.plugins.dcs_world_plugin.dcs_world as dcs


class TestDCSParseTest(unittest.TestCase):
    def setUp(self):
        self.dcs_instance = dcs.DCSWorldParser("./tests/data/dcs_world/valid_dcs_world_directory")

    def test_no_profiles_parsed(self):
        pass

    def test_button_convert_button(self):
        button = self.dcs_instance.convert_button_format("JOY_BTN2")
        self.assertEqual(button, "BUTTON_2")

        button = self.dcs_instance.convert_button_format("JOY_BTN59")
        self.assertEqual(button, "BUTTON_59")

    def test_button_convert_axis(self):
        button = self.dcs_instance.convert_button_format("JOY_RZ")
        self.assertEqual(button, "AXIS_RZ")

        button = self.dcs_instance.convert_button_format("JOY_Z")
        self.assertEqual(button, "AXIS_Z")

    def test_button_convert_pov(self):
        button = self.dcs_instance.convert_button_format("JOY_BTN_POV1_UR")
        self.assertEqual(button, "POV_1_UR")

        button = self.dcs_instance.convert_button_format("JOY_BTN_POV2_UR")
        self.assertEqual(button, "POV_2_UR")


if __name__ == "__main__":
    unittest.main()
