import unittest
import adaptors.star_citizen as sc


class TestSCParserCases(unittest.TestCase):
    def setUp(self):
        self.file = sc.StarCitizen("./tests/data/star_citizen/layout_all_exported_valid.xml")
        self.file.devices = {
            "js1": {"guid": "0000000", "name": "Joystick"},
            "kb1": {"guid": "1111111", "name": "Keyboard"},
        }

    def test_device_id_keyboard(self):
        check = self.file.device_id("keyboard", 1)
        self.assertEqual(check, "kb1")

        check = self.file.device_id("keyboard", 2)
        self.assertEqual(check, "kb2")

    def test_device_id_joystick(self):
        check = self.file.device_id("joystick", 1)
        self.assertEqual(check, "js1")

        check = self.file.device_id("joystick", 2)
        self.assertEqual(check, "js2")

    def test_device_id_invalid(self):
        check = self.file.device_id("potato", 1)
        self.assertEqual(check, "mo1")

        check = self.file.device_id("potato", 2)
        self.assertEqual(check, "mo2")

    def test_bind_parse_button(self):
        data = self.file.parse_map("js1_button1")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "BUTTON_1"))

        data = self.file.parse_map("js1_button22")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "BUTTON_22"))

        data = self.file.parse_map("js1_button999")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "BUTTON_999"))

    def test_bind_parse_blank(self):
        data = self.file.parse_map("js1_")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, None))

    def test_bind_parse_hat(self):
        data = self.file.parse_map("js1_hat1_up")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "POV_1_U"))

        data = self.file.parse_map("js1_hat1_right")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "POV_1_R"))

        data = self.file.parse_map("js1_hat1_down")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "POV_1_D"))

        data = self.file.parse_map("js1_hat1_left")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "POV_1_L"))

    def test_bind_parse_axis(self):
        data = self.file.parse_map("js1_rotz")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "AXIS_Rz"))

        data = self.file.parse_map("js1_x")
        self.assertEqual(data, ({"guid": "0000000", "name": "Joystick"}, "AXIS_x"))

        data = self.file.parse_map("js1_slider1")
        self.assertEqual(
            data, ({"guid": "0000000", "name": "Joystick"}, "AXIS_SLIDER_1")
        )

    def test_bind_no_device(self):
        data = self.file.parse_map("abc_hat1_up")
        self.assertEqual(data, (None, None))

    def test_parser(self):
        expected = {
            "VKB-Sim Gladiator NXT R": {
                "Default": {
                    "Axis": "",
                    "Buttons": {
                        "BUTTON_1": "Close all doors",
                        "BUTTON_2": "Open all doors",
                        "BUTTON_3": "Unlock doors",
                        "BUTTON_4": "Look_behind",
                    },
                    "Inherit": False,
                }
            },
            "VKB-Sim Gladiator NXT L": {
                "Default": {
                    "Axis": "",
                    "Buttons": {
                        "AXIS_Rx": "View yaw",
                        "AXIS_Ry": "View pitch",
                        "BUTTON_1": "View cycle fwd",
                        "BUTTON_2": "View dyn zoom abs",
                        "BUTTON_22": "Cruise control",
                    },
                    "Inherit": False,
                }
            },
        }

        data = self.file.parse()
        self.maxDiff = None
        self.assertEqual(expected, data)


if __name__ == "__main__":
    unittest.main()
