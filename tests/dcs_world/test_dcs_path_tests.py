import unittest
import adaptors.dcs_world as dcs
class TestDCS_Paths(unittest.TestCase):

    def setUp(self):
        pass

    def test_no_config_path(self):
        with self.assertRaises(Exception) as context:
            dcs.DCSWorld_Parser('./tests/data/dcs_world/Invalid_DCS_World_No_Config')
        self.assertTrue('DCS: No Config Folder found in DCS Folder' in str(context.exception))

    def test_no_joystick_directory(self):
        with self.assertRaises(Exception) as context:
            dcs.DCSWorld_Parser('./tests/data/dcs_world/Invalid_DCS_World_No_Input')
        self.assertTrue('DCS: No input directory found' in str(context.exception))

    def test_no_files_in_directory(self):
        with self.assertRaises(Exception) as context:
            dcs.DCSWorld_Parser('./tests/data/dcs_world/Invalid_DCS_World_No_Profiles')
        self.assertTrue('DCS: No profiles exist in Input directory!' in str(context.exception))
if __name__ == '__main__':
    unittest.main()