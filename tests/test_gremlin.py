import unittest
import adaptors.gremlin as gremlin

class TestGremlin(unittest.TestCase):

    def setUp(self):
        self.file = gremlin.Gremlin("./tests/data/gremlin_test.xml")

    def test_number_devices(self):
        self.assertEqual(7,self.file.getDeviceCount())

if __name__ == '__main__':
    unittest.main()