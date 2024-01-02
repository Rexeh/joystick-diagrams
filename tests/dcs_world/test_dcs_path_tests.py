import os
import shutil
import unittest

import joystick_diagrams.plugins.dcs_world_plugin.dcs_world as dcs


class TestDCSPaths(unittest.TestCase):
    def setUp(self):
        pass

    def test_no_config_path(self):
        with self.assertRaises(Exception) as context:
            dcs.DCSWorldParser("./tests/data/dcs_world/invalid_dcs_world_no_config")
        self.assertTrue("DCS: No Config Folder found in DCS Folder" in str(context.exception))

    def test_no_joystick_directory(self):
        with self.assertRaises(Exception) as context:
            dcs.DCSWorldParser("./tests/data/dcs_world/invalid_dcs_world_no_input")
        self.assertTrue("DCS: No input directory found" in str(context.exception))

    def test_no_files_in_directory(self):
        if os.path.exists("./tests/data/dcs_world/dynamic_folder_creation"):
            shutil.rmtree("./tests/data/dcs_world/dynamic_folder_creation")

        os.mkdir("./tests/data/dcs_world/dynamic_folder_creation")
        os.mkdir("./tests/data/dcs_world/dynamic_folder_creation/Config")
        os.mkdir("./tests/data/dcs_world/dynamic_folder_creation/Config/Input")

        with self.assertRaises(Exception) as context:
            dcs.DCSWorldParser("./tests/data/dcs_world/dynamic_folder_creation")
        self.assertTrue("DCS: No profiles exist in Input directory!" in str(context.exception))


if __name__ == "__main__":
    unittest.main()
