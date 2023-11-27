import unittest
import joystick_diagrams.adaptors.star_citizen.star_citizen as sc


class TestSCFileErrors(unittest.TestCase):
    def test_empty_file(self):
        with self.assertRaises(Exception) as context:
            sc.StarCitizen("./tests/data/star_citizen/empty.xml")
        self.assertTrue("File is not a valid Star Citizen XML" in str(context.exception))

    def test_invalid_file(self):
        with self.assertRaises(Exception) as context:
            sc.StarCitizen("./tests/data/star_citizen/invalid.xml")
        self.assertTrue("File is not a valid Star Citizen XML" in str(context.exception))

    def test_invalid_file_type(self):
        with self.assertRaises(Exception) as context:
            sc.StarCitizen("./tests/data/star_citizen/invalid_type.abc")
        self.assertTrue("File must be an XML file" in str(context.exception))

    def test_invalid_file_path(self):
        with self.assertRaises(Exception) as context:
            sc.StarCitizen("./tests/data/star_citizen/not_a_file.file")
        self.assertTrue("File not found" in str(context.exception))


if __name__ == "__main__":
    unittest.main()
