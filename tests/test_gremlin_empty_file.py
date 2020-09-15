import unittest
import adaptors.gremlin as gremlin

class TestGremlin_No_Devices(unittest.TestCase):

    no_inherit_expected = {   
    }

    def setUp(self):
        self.file = gremlin.Gremlin("./tests/data/gremlin_no_devices.xml")

    def test_number_devices(self):
        self.assertEqual(0,self.file.getDeviceCount())

    # Not a unit test, revisit later if needed
    def test_device_object(self):
        self.maxDiff = None
        self.parsedFile = self.file.createDictionary()
        self.assertEqual(self.no_inherit_expected,self.parsedFile )

if __name__ == '__main__':
    unittest.main()