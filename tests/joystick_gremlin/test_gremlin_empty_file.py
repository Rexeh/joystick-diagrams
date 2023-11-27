import unittest
import joystick_diagrams.adaptors.joystick_gremlin.joystick_gremlin as gremlin


class TestGremlinNoDevices(unittest.TestCase):
    no_inherit_expected: dict = {}

    def setUp(self):
        self.file = gremlin.JoystickGremlin("./tests/data/joystick_gremlin/gremlin_no_devices.xml")

    def test_number_devices(self):
        self.assertEqual(0, self.file.get_device_count())

    # Not a unit test, revisit later if needed
    def test_device_object(self):
        parsed_file = self.file.create_dictionary()
        self.assertEqual(self.no_inherit_expected, parsed_file)


if __name__ == "__main__":
    unittest.main()
