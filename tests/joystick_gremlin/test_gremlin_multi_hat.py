import unittest
import adaptors.joystick_gremlin as gremlin

class TestGremlin_Multiple_Hats(unittest.TestCase):

    expected = {
        'VPC Stick MT-50CM': {
        'Default' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'DESC1',
                'BUTTON_2': 'DESC2',
                'POV_1_U': 'BUTTON U',
                'POV_1_UR': 'Hat Switch 1',
                'POV_1_R': 'Hat Switch 1',
                'POV_1_DR': 'Hat Switch 1',
                'POV_1_D': 'BUTTON D',
                'POV_1_DL': 'Hat Switch 1',
                'POV_1_L': 'Hat Switch 1',
                'POV_1_UL': 'Hat Switch 1',
                'POV_2_U': 'BUTTON U',
                'POV_2_R': 'Hat Switch 2',
                'POV_2_D': 'BUTTON D',
                'POV_2_L': 'Hat Switch 2',
            },
            'Inherit' : False
        }
        }
    }
    def setUp(self):
        self.file = gremlin.JoystickGremlin("./tests/data/joystick_gremlin/gremlin_pov_multi.xml")

    def test_pov_multi_hats(self):
        self.maxDiff = None
        self.parsedFile = self.file.createDictionary()
        self.assertEqual(self.expected,self.parsedFile)
        

if __name__ == '__main__':
    unittest.main()