import unittest

import joystick_diagrams.plugins.star_citizen_plugin.star_citizen as sc


class TestSCParserCases(unittest.TestCase):
    def setUp(self):
        self.file = sc.StarCitizen("./tests/data/star_citizen/layout_all_exported_valid.xml")

    def test_bind_parse_button(self):
        # ("js1_button1")
        # ("js1_button22")
        # ("js1_button999")
        pass

    def test_bind_parse_blank(self):
        # ("js1_")
        pass

    def test_bind_parse_hat(self):
        # "js1_hat1_up")
        # ("js1_hat1_right")
        # "js1_hat1_down")
        # "js1_hat1_left")
        pass

    def test_bind_parse_axis(self):
        # "js1_rotz")
        # "js1_x")
        # "js1_slider1")
        pass

    def test_bind_no_device(self):
        pass

    def test_parser(self):
        pass


if __name__ == "__main__":
    unittest.main()
