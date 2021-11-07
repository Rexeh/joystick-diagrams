import unittest
import joystick_diagrams.adaptors.joystick_gremlin as gremlin


class TestGremlin_No_Devices(unittest.TestCase):

    no_inherit_expected = {}

    def setUp(self):
        self.file = gremlin.JoystickGremlin("./tests/data/joystick_gremlin/gremlin_no_devices.xml")

    def test_number_devices(self):
        self.assertEqual(0, self.file.get_device_count())

    # Not a unit test, revisit later if needed
    def test_device_object(self):
        self.maxDiff = None
        self.parsedFile = self.file.create_dictionary()
        self.assertEqual(self.no_inherit_expected, self.parsedFile)


if __name__ == "__main__":
    unittest.main()
