import datetime
import os
import tempfile
import unittest

from joystick_diagrams.classes import export


class TestExportTemplate(unittest.TestCase):
    data = {
        "VPC Throttle MT-50 CM2": {
            "A10": {
                "Axis": "",
                "Buttons": {
                    "BUTTON_1": "Button 1 - No Replace",
                    "BUTTON_2": "Base Replacement",
                    "BUTTON_3": "NO BIND",
                    "BUTTON_4": "NO BIND",
                    "BUTTON_5": "Pinkie Center",
                    "BUTTON_6": "Pinkie Forward",
                    "BUTTON_7": "Pinkie Aft",
                    "BUTTON_56": "A10 Mode",
                    "BUTTON_57": "F18 Mode",
                    "BUTTON_58": "KA50 Mode",
                },
                "Inherit": "Base",
            },
            "Base": {
                "Axis": "",
                "Buttons": {
                    "BUTTON_1": "Base No Replace",
                    "BUTTON_2": "Base Replacement",
                    "BUTTON_56": "A10 Mode",
                    "BUTTON_57": "F18 Mode",
                    "BUTTON_58": "KA50 Mode",
                },
                "Inherit": False,
            },
        },
        "Other Device No Template": "",
    }

    def setUp(self):
        self.exporter = export.Export(self.data)
        self.template = tempfile.TemporaryDirectory()
        self.exporter.export_directory = self.template.name + "/"

    def test_files_exported(self):
        self.exporter.export_config()
        self.assertEqual(len(self.exporter.error_bucket), 1)
        self.assertEqual(
            self.exporter.error_bucket[0],
            "No Template file found for: Other Device No Template",
        )
        self.assertEqual(len(os.listdir(self.template.name)), 2)

    def test_files_exported_no_directory(self):
        self.exporter.export_directory = self.template.name + "/new/"
        self.exporter.export_config()
        self.assertEqual(len(os.listdir(self.template.name + "/new/")), 2)

    def test_unused_strings_replaced(self):
        data = self.exporter.replace_unused_strings("<Item>BUTTON_26</Item>Some Text - Some more Text BUTTON_87")
        self.assertEqual(data, "<Item>No Bind</Item>Some Text - Some more Text No Bind")

    def test_unused_strings_replaced_custom_text(self):
        self.exporter.no_bind_text = "OVERRIDE"
        data = self.exporter.replace_unused_strings("<Item>BUTTON_26</Item>Some Text - Some more Text BUTTON_87")
        self.assertEqual(data, "<Item>OVERRIDE</Item>Some Text - Some more Text OVERRIDE")

    def test_string_replacement(self):
        data = self.exporter.replace_template_strings(
            "VPC Throttle MT-50 CM2",
            "A10",
            "<XML><BUTTON_1><BUTTON_5><BUTTON_56><BUTTON_56><BUTTON_58>",
        )
        self.assertEqual(
            data,
            "<XML><Button 1 - No Replace><Pinkie Center><A10 Mode><A10 Mode><KA50 Mode>",
        )

    def test_string_replacement_no_bind(self):
        self.exporter.no_bind_text = "OVERRIDE"
        data = self.exporter.replace_template_strings(
            "VPC Throttle MT-50 CM2",
            "A10",
            "<XML><BUTTON_3><BUTTON_4><BUTTON_56><BUTTON_58>",
        )
        self.assertEqual(data, "<XML><OVERRIDE><OVERRIDE><A10 Mode><KA50 Mode>")

    def test_branding_replace(self):
        self.exporter.no_bind_text = "OVERRIDE"
        data = self.exporter.brand_template("ABC 123 -/12-a", "<XML><SOME><STUFF><TEMPLATE_NAME></XML>")
        self.assertEqual(data, "<XML><SOME><STUFF><ABC 123 -/12-a></XML>")

    def test_get_template_success(self):
        data = self.exporter.get_template("VPC Throttle MT-50 CM2")
        self.assertGreater(data, "")

    def test_get_template_white_space_success(self):
        data = self.exporter.get_template(" VPC Throttle MT-50 CM2  ")
        self.assertGreater(data, "")

    def test_get_template_failure(self):
        data = self.exporter.get_template("Not a Template")
        self.assertEqual(data, False)

    def test_template_date(self):
        dt = datetime.datetime.now().strftime("%d/%m/%Y")
        temp = self.exporter.date_template("XYZ CURRENT_DATE XYZ")
        assert dt in temp


if __name__ == "__main__":
    unittest.main()
