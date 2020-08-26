import unittest
import adaptors.gremlin as gremlin

class TestGremlin(unittest.TestCase):

    expectedFileObject = {   
        'VPC Throttle MT-50 CM2': {
        'A10' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'NO BIND',
                'BUTTON_2': 'NO BIND',
                'BUTTON_3': 'NO BIND',
                'BUTTON_4': 'NO BIND',
                'BUTTON_5': 'Pinkie Center',
                'BUTTON_6': 'Pinkie Forward',
                'BUTTON_7': 'Pinkie Aft'
            }
        },
        'Base' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_56': 'A10 Mode',
                'BUTTON_57': 'F18 Mode',
                'BUTTON_58': 'KA50 Mode'
            }
        },
        'FA18' : {
            'Axis' : '',
            'Buttons': {}
        },
        'KA50' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1' : 'HUD Mode',
                'BUTTON_2' : 'HUD Brightness Down',
                'BUTTON_55' : 'IT-23 contrast Up',
                'BUTTON_56' : 'NO BIND',
                'BUTTON_57' : 'NO BIND'
            }
        }
    },
        'VPC Stick MT-50CM': {
                    'A10' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'Trim Up',
                'BUTTON_2': 'Trim Right'
            }
        },

        'Base' : {
            'Axis' : '',
            'Buttons': {
                'BUTTON_1': 'NO BIND',
                'BUTTON_2': 'NO BIND'
            }
        },

        'FA18' : {
            'Axis' : '',
            'Buttons': {}
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
            }
        },  
        }
    }

    def setUp(self):
        self.file = gremlin.Gremlin("./tests/data/gremlin_test.xml")

    def test_number_devices(self):
        self.assertEqual(2,self.file.getDeviceCount())

    def test_device_object(self):
        self.maxDiff = None
        self.assertEqual(self.expectedFileObject, self.file.createDictionary())

if __name__ == '__main__':
    unittest.main()