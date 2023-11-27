import unittest
import joystick_diagrams.adaptors.joystick_gremlin.joystick_gremlin as gremlin


class TestGremlinSingleHat(unittest.TestCase):
    expected = {
        "VPC Stick MT-50CM": {
            "Default": {
                "Axis": "",
                "Buttons": {
                    "BUTTON_1": "DESC1",
                    "BUTTON_2": "DESC2",
                    "POV_1_U": "BUTTON U",
                    "POV_1_UR": "Hat Switch",
                    "POV_1_R": "Hat Switch",
                    "POV_1_DR": "Hat Switch",
                    "POV_1_D": "BUTTON D",
                    "POV_1_DL": "Hat Switch",
                    "POV_1_L": "Hat Switch",
                    "POV_1_UL": "Hat Switch",
                },
                "Inherit": False,
            }
        }
    }

    def setUp(self):
        self.file = gremlin.JoystickGremlin("./tests/data/joystick_gremlin/gremlin_pov_single.xml")

    def test_pov_single_8_way(self):
        parsed_file = self.file.create_dictionary()
        self.assertEqual(self.expected, parsed_file)


if __name__ == "__main__":
    unittest.main()
