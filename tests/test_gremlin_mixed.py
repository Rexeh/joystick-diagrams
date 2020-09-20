import unittest
import adaptors.joystick_gremlin as gremlin

class TestGremlin_Mixed(unittest.TestCase):

    inherit_no_inherit_expected = {   
        'VPC Throttle MT-50 CM2': {
        'A10' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'Button 1 - No Replace',
                'BUTTON_2': 'Base Replacement',
                'BUTTON_3': 'NO BIND',
                'BUTTON_4': 'NO BIND',
                'BUTTON_5': 'Pinkie Center',
                'BUTTON_6': 'Pinkie Forward',
                'BUTTON_7': 'Pinkie Aft',
                'BUTTON_56': 'A10 Mode',
                'BUTTON_57': 'F18 Mode',
                'BUTTON_58': 'KA50 Mode',
            },
            'Inherit' : 'Base'
        },
        'Base' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1' : 'Base No Replace',
                'BUTTON_2' : 'Base Replacement',
                'BUTTON_56': 'A10 Mode',
                'BUTTON_57': 'F18 Mode',
                'BUTTON_58': 'KA50 Mode'
            },
            'Inherit' : False
        },
        'FA18' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1' : 'Base No Replace',
                'BUTTON_2' : 'Base Replacement',
                'BUTTON_56': 'A10 Mode',
                'BUTTON_57': 'F18 Mode',
                'BUTTON_58': 'KA50 Mode'
            },
            'Inherit' : 'Base'
        },
        'KA50' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1' : 'KA50 Button 1',
                'BUTTON_2' : 'KA50 Button 2',
                'BUTTON_55' : 'KA50 Button 55',
                'BUTTON_56' : 'NO BIND',
                'BUTTON_57' : 'NO BIND'
            },
            'Inherit' : False
        }
    },
        'VPC Stick MT-50CM': {
            'A10' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'Trim Up',
                'BUTTON_2': 'Trim Right'
            },
            'Inherit' : False
        },

        'Base' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'NO BIND',
                'BUTTON_2': 'NO BIND'
            },
            'Inherit' : False
        },

        'FA18' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'NO BIND',
                'BUTTON_2': 'NO BIND'
            },
            'Inherit' : 'Base'
        },

        'KA50' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'NO BIND',
                'BUTTON_2': 'NO BIND',
                'BUTTON_3': 'NO BIND',
                'BUTTON_4': 'NO BIND',
                'BUTTON_5': 'NO BIND',
                'BUTTON_6': 'Gun Fire'
            },
            'Inherit' : 'Base'
        },  
        }
    }

    def setUp(self):
        self.file = gremlin.JoystickGremlin("./tests/data/gremlin_inherit_no_inherit.xml")

    def test_number_devices(self):
        self.assertEqual(2,self.file.getDeviceCount())

    # Not a unit test, revisit later if needed
    def test_device_object(self):
        self.maxDiff = None
        self.parsedFile = self.file.createDictionary()
        self.assertEqual(self.inherit_no_inherit_expected,self.parsedFile )

if __name__ == '__main__':
    unittest.main()