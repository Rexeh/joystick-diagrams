from os import path
import os
from pathlib import Path
import re
import html
import functions.helper as helper

class Export:

    def __init__(self, joystick_listing, parser_id="UNKNOWN", custom_no_bind="No Bind"):
        self.export_directory = './diagrams/'
        self.templates_directory = './templates/'
        self.file_name_divider = "_"
        self.joystick_listing = joystick_listing
        self.export_progress = None
        self.no_bind_text = custom_no_bind
        self.executor = parser_id
        self.error_bucket = []

    def export_config(self):
        for joystick in self.joystick_listing:
            base_template = self.get_template(joystick)
            if base_template:
                for mode in self.joystick_listing[joystick]:
                    write_template = base_template
                    completed_template = self.replace_template_strings(joystick, mode, write_template)
                    completed_template = self.replace_unused_strings(completed_template)
                    completed_template = self.brand_template(mode, completed_template)
                    self.save_template(joystick,mode,completed_template)
            else:
                self.error_bucket.append("No Template for: {}".format(joystick))
        return self.error_bucket

    def create_directory(self,directory):
        if not os.path.exists(directory):
            try:
                return os.makedirs(directory)
            except PermissionError as e:
                helper.log(e, "error")
                raise
            else:
                return False
        else:
            return False

    def get_template(self, joystick):
        if path.exists(self.templates_directory + joystick + ".svg"):
            data = Path(os.path.join(self.templates_directory, joystick + ".svg")).read_text(encoding="utf-8")
            return data
        else:
            return False

    def save_template(self, joystick, mode, template):
        output_path = self.export_directory + self.executor + "_" + joystick + "_" + mode + ".svg"
        if not os.path.exists(self.export_directory):
            self.create_directory(self.export_directory)
        try:
            outputfile = open(output_path, "w", encoding="UTF-8")
            outputfile.write(template)
            outputfile.close()
        except PermissionError as e:
            helper.log(e, 'error')
            raise

    def replace_unused_strings(self, template):
  
        regex_search = "\\bButton_\d+\\b"
        matches = re.findall(regex_search, template, flags=re.IGNORECASE)
        matches = list(dict.fromkeys(matches))
        for i in matches:
            search = "\\b" + i + "\\b"
            template = re.sub(search, html.escape(self.no_bind_text), template, flags=re.IGNORECASE)
        return template

    def replace_template_strings(self,device,mode, template):
        for b, v in self.joystick_listing[device][mode]['Buttons'].items():
            if v == "NO BIND":
                v = self.no_bind_text
            regexSearch = "\\b" + b + "\\b"
            template = re.sub(regexSearch, html.escape(v), template, flags=re.IGNORECASE)
        return template

    def brand_template(self, title, template):
        template = re.sub("\\bTEMPLATE_NAME\\b", title, template)
        return template