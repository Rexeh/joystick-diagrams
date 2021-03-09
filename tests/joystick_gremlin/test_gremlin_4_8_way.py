import unittest
import adaptors.joystick_gremlin as gremlin

class TestGremlin_No_Devices(unittest.TestCase):

    no_inherit_expected = {   
    }

    def setUp(self):
        self.file = gremlin.JoystickGremlin("./tests/data/joystick_gremlin/gremlin_no_devices.xml")
    
    # TODO

if __name__ == '__main__':
    unittest.main()