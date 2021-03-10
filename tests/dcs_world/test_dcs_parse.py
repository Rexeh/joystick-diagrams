import unittest
import adaptors.dcs_world as dcs
import pprint

class TestDCS_Parse_Test(unittest.TestCase):

    def setUp(self):
        self.dcs_instance = dcs.DCSWorld_Parser('./tests/data/dcs_world/valid_dcs_world_directory')
        self.maxDiff = None

    def test_no_profiles_selected_no_easy(self):
        '''Test default no selection, with easy modes disabled (excluded)'''
        profiles = self.dcs_instance.getValidatedProfiles()

        expected = {
                    'Throttle - HOTAS Warthog': {
                        'CoolPlane-A': {
                            'Buttons': {
                                'BUTTON_22': 'FLAP Switch - UP else STOP',
                                'BUTTON_23': 'FLAP Switch - DOWN else STOP',
                                'AXIS_SLIDER_1' : 'Zoom View'
                            },
                            'Axis': '',
                            'Inherit': False
                            },
                        'CoolPlane-B': {
                            'Buttons': {
                                'BUTTON_15': 'Thrust Reverser On/Off',
                                'BUTTON_26': 'Master caution reset',
                                'AXIS_RZ': 'Thrust',
                                'AXIS_SLIDER_1' : 'Zoom View',
                                'AXIS_X' : 'Radar stick horizontal',
                                'AXIS_Y' : 'Radar stick vertical'
                                },
                                'Axis': '',
                                'Inherit': False
                                }
                            },
                    'Joystick - HOTAS Warthog': {
                        'CoolPlane-B': {
                            'Buttons': {
                                'BUTTON_19': 'Fast countermeasure dispense',
                                'BUTTON_5': 'Reference button',
                                'AXIS_Y' : 'Pitch',
                                'AXIS_X' : 'Roll'
                            },
                            'Axis': '',
                            'Inherit': False
                            }
                            }
                            }

        data = self.dcs_instance.processProfiles()
        self.assertEqual(data,expected)


    def test_no_profiles_selected_including_easy_modes(self):
        '''Test default no selection, with easy modes enabled (included)'''
        profiles = self.dcs_instance.getValidatedProfiles()
        expected = {'Throttle - HOTAS Warthog': {'CoolPlane-A': {'Buttons': {'BUTTON_22': 'FLAP Switch - UP else STOP', 'BUTTON_23': 'FLAP Switch - DOWN else STOP', 'AXIS_SLIDER_1' : 'Zoom View'}, 'Axis': '', 'Inherit': False}, 'CoolPlane-B': {'Buttons': {'BUTTON_15': 'Thrust Reverser On/Off', 'BUTTON_26': 'Master caution reset', 'AXIS_RZ' : 'Thrust', 'AXIS_SLIDER_1' : 'Zoom View', 'AXIS_X' : 'Radar stick horizontal', 'AXIS_Y' : 'Radar stick vertical'}, 'Axis': '', 'Inherit': False}, 'CoolPlane-E_easy': {'Buttons': {'BUTTON_26': 'External Cargo Pilot Unhook', 'BUTTON_27': 'Pilot Sight Armed/Docked', 'BUTTON_28': 'Pilot Sight Switch', 'BUTTON_4': 'Intercom Mode Selector (rotary)', 'BUTTON_32': 'Start-up engine', 'BUTTON_10': 'Search light Off', 'BUTTON_9': 'Search light On', 'BUTTON_8': 'Search light Retract', 'BUTTON_7': 'Search light Extend', 'AXIS_SLIDER_1' : 'Zoom View', 'AXIS_Z' : 'Flight Control Collective', 'AXIS_RZ' : 'Throttle' }, 'Axis': '', 'Inherit': False}}, 'Joystick - HOTAS Warthog': {'CoolPlane-B': {'Buttons': {'BUTTON_19': 'Fast countermeasure dispense', 'BUTTON_5': 'Reference button', 'AXIS_Y' : 'Pitch', 'AXIS_X' : 'Roll'}, 'Axis': '', 'Inherit': False}, 'CoolPlane-E_easy': {'Buttons': {'BUTTON_11': 'Pilot Trimmer', 'BUTTON_4': 'Flare Dispense Button', 'BUTTON_1': 'Pilot weapon release/Machinegun fire', 'BUTTON_9': 'Pilot Sight Elevation Decrease', 'BUTTON_7': 'Pilot Sight Elevation Increase', 'BUTTON_18': 'Throttle Down', 'BUTTON_16': 'Throttle Up', 'AXIS_Y' : 'Flight Control Cyclic Pitch', 'AXIS_X' : 'Flight Control Cyclic Roll'}, 'Axis': '', 'Inherit': False}}, }

        self.dcs_instance.remove_easy_modes = False
        data = self.dcs_instance.processProfiles()
        self.assertEqual(data,expected)

    def test_single_profile_selected(self):
        profiles = self.dcs_instance.getValidatedProfiles()

        expected = {
        'Throttle - HOTAS Warthog': {
            'CoolPlane-A': {
                'Buttons': {
                    'BUTTON_22': 'FLAP Switch - UP else STOP',
                    'BUTTON_23': 'FLAP Switch - DOWN else STOP',
                    'AXIS_SLIDER_1' : 'Zoom View'
                },
                'Axis': '',
                'Inherit': False
                },
                }
            }

        data = self.dcs_instance.processProfiles([profiles[0]])
        self.assertEqual(data, expected)
        # Single Profile with Easy Mode on
        # Single Profile with Easy Mode off


    def test_double_profile_selected(self):
        profiles = self.dcs_instance.getValidatedProfiles()

        expected = {
                    'Throttle - HOTAS Warthog': {
                        'CoolPlane-A': {
                            'Buttons': {
                                'BUTTON_22': 'FLAP Switch - UP else STOP',
                                'BUTTON_23': 'FLAP Switch - DOWN else STOP',
                                'AXIS_SLIDER_1' : 'Zoom View'
                            },
                            'Axis': '',
                            'Inherit': False
                            },
                        'CoolPlane-B': {
                            'Buttons': {
                                'BUTTON_15': 'Thrust Reverser On/Off',
                                'BUTTON_26': 'Master caution reset',
                                'AXIS_RZ': 'Thrust',
                                'AXIS_SLIDER_1' : 'Zoom View',
                                'AXIS_X' : 'Radar stick horizontal',
                                'AXIS_Y' : 'Radar stick vertical'
                                },
                                'Axis': '',
                                'Inherit': False
                                }
                            },
                    'Joystick - HOTAS Warthog': {
                        'CoolPlane-B': {
                            'Buttons': {
                                'BUTTON_19': 'Fast countermeasure dispense',
                                'BUTTON_5': 'Reference button',
                                'AXIS_Y' : 'Pitch',
                                'AXIS_X' : 'Roll'
                            },
                            'Axis': '',
                            'Inherit': False
                            }
                            }
                            }

        data = self.dcs_instance.processProfiles([profiles[0],profiles[1]])
        self.assertEqual(data, expected)
    def test_no_profiles_parsed(self):
        pass

    def test_button_convert_button(self):
        
        button = self.dcs_instance.convert_button_format("JOY_BTN2")
        self.assertEqual(button, "BUTTON_2")

        button = self.dcs_instance.convert_button_format("JOY_BTN59")
        self.assertEqual(button, "BUTTON_59")      

    def test_button_convert_axis(self):
        
        button = self.dcs_instance.convert_button_format("JOY_RZ")
        self.assertEqual(button, "AXIS_RZ")

        button = self.dcs_instance.convert_button_format("JOY_Z")
        self.assertEqual(button, "AXIS_Z")      
        
    def test_button_convert_pov(self):
        
        button = self.dcs_instance.convert_button_format("JOY_BTN_POV1_UR")
        self.assertEqual(button, "POV_1_UR")

        button = self.dcs_instance.convert_button_format("JOY_BTN_POV2_UR")
        self.assertEqual(button, "POV_2_UR")             
        

if __name__ == '__main__':
    unittest.main()