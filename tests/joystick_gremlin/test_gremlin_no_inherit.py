import unittest
import joystick_diagrams.adaptors.joystick_gremlin as gremlin


class TestGremlin_No_Inherit(unittest.TestCase):

    no_inherit_expected = {
        "VPC Throttle MT-50 CM2": {
            "A10": {
                "Axis": "",
                "Buttons": {
                    "BUTTON_1": "NO BIND",
                    "BUTTON_2": "NO BIND",
                    "BUTTON_3": "NO BIND",
                    "BUTTON_4": "NO BIND",
                    "BUTTON_5": "Pinkie Center",
                    "BUTTON_6": "Pinkie Forward",
                    "BUTTON_7": "Pinkie Aft",
                },
                "Inherit": False,
            },
            "FA18": {"Axis": "", "Buttons": {}, "Inherit": False},
            "KA50": {
                "Axis": "",
                "Buttons": {
                    "BUTTON_1": "HUD Mode",
                    "BUTTON_2": "HUD Brightness Down",
                    "BUTTON_55": "IT-23 contrast Up",
                    "BUTTON_56": "NO BIND",
                    "BUTTON_57": "NO BIND",
                },
                "Inherit": False,
            },
        },
        "VPC Stick MT-50CM": {
            "A10": {
                "Axis": "",
                "Buttons": {"BUTTON_1": "Trim Up", "BUTTON_2": "Trim Right"},
                "Inherit": False,
            },
            "FA18": {"Axis": "", "Buttons": {}, "Inherit": False},
            "KA50": {
                "Axis": "",
                "Buttons": {
                    "BUTTON_1": "NO BIND",
                    "BUTTON_2": "NO BIND",
                    "BUTTON_3": "NO BIND",
                    "BUTTON_4": "NO BIND",
                    "BUTTON_5": "NO BIND",
                    "BUTTON_6": "Gun Fire",
                },
                "Inherit": False,
            },
        },
    }

    def setUp(self):
        self.file = gremlin.JoystickGremlin(
            "./tests/data/joystick_gremlin/gremlin_no_inherit.xml"
        )

    def test_number_devices(self):
        self.assertEqual(2, self.file.get_device_count())

    # Not a unit test, revisit later if needed
    def test_device_object(self):
        self.maxDiff = None
        self.parsedFile = self.file.create_dictionary()
        self.assertEqual(self.no_inherit_expected, self.parsedFile)


if __name__ == "__main__":
    unittest.main()
