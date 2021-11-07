from os import path
import os
from pathlib import Path
import re
import html
import logging
from PyQt5 import QtWidgets
from joystick_diagrams import config

_logger = logging.getLogger(__name__)


class Export:
    def __init__(self, joystick_listing, parser_id="UNKNOWN"):
        self.export_directory = "./diagrams/"
        self.templates_directory = "./templates/"
        self.file_name_divider = "_"
        self.joystick_listing = joystick_listing
        self.export_progress = None
        self.no_bind_text = config.noBindText
        self.executor = parser_id
        self.error_bucket = []

    def export_config(self, progress_bar=None) -> list:

        joystick_count = len(self.joystick_listing)

        _logger.debug("Export Started with {} joysticks".format(joystick_count))
        _logger.debug("Export Data: {}".format(self.joystick_listing))

        if isinstance(progress_bar, QtWidgets.QProgressBar):
            progress_bar.setValue(0)
            progress_increment = 100 / joystick_count

        for joystick in self.joystick_listing:
            base_template = self.get_template(joystick)
            if base_template:
                progress_increment_modes = len(self.joystick_listing[joystick])
                for mode in self.joystick_listing[joystick]:
                    write_template = base_template
                    print("Replacing Strings")
                    completed_template = self.replace_template_strings(joystick, mode, write_template)
                    print("Replacing Unused String")
                    completed_template = self.replace_unused_strings(completed_template)
                    print("Branding")
                    completed_template = self.brand_template(mode, completed_template)
                    print("Saving: {}".format(joystick))
                    self.save_template(joystick, mode, completed_template)
                    if isinstance(progress_bar, QtWidgets.QProgressBar):
                        progress_bar.setValue(progress_bar.value() + (progress_increment / progress_increment_modes))
            else:
                self.error_bucket.append("No Template file found for: {}".format(joystick))

            if isinstance(progress_bar, QtWidgets.QProgressBar):
                progress_bar.setValue(progress_bar.value() + progress_increment)

        if isinstance(progress_bar, QtWidgets.QProgressBar):
            progress_bar.setValue(100)
        return self.error_bucket

    def create_directory(self, directory) -> bool:
        if not os.path.exists(directory):
            try:
                return os.makedirs(directory)
            except PermissionError as e:
                _logger.error(e)
                raise
            else:
                return False
        else:
            return False

    def get_template(self, joystick):
        joystick = joystick.strip()
        if path.exists(self.templates_directory + joystick + ".svg"):
            data = Path(os.path.join(self.templates_directory, joystick + ".svg")).read_text(encoding="utf-8")
            return data
        else:
            return False

    def save_template(self, joystick, mode, template):
        output_path = self.export_directory + self.executor + "_" + joystick.strip() + "_" + mode + ".svg"
        if not os.path.exists(self.export_directory):
            self.create_directory(self.export_directory)
        try:
            outputfile = open(output_path, "w", encoding="UTF-8")
            outputfile.write(template)
            outputfile.close()
        except PermissionError as e:
            _logger.error(e)
            raise

    def replace_unused_strings(self, template):
        regex_search = "\\bButton_\\d+\\b|\\bPOV_\\d+_\\w+\\b"
        matches = re.findall(regex_search, template, flags=re.IGNORECASE)
        matches = list(dict.fromkeys(matches))
        if matches:
            for i in matches:
                search = "\\b" + i + "\\b"
                template = re.sub(
                    search,
                    html.escape(self.no_bind_text),
                    template,
                    flags=re.IGNORECASE,
                )
        return template

    def replace_template_strings(self, device, mode, template):
        for button, value in self.joystick_listing[device][mode]["Buttons"].items():
            if value == "NO BIND":
                value = self.no_bind_text
            regex_search = "\\b" + button + "\\b"
            template = re.sub(regex_search, html.escape(value), template, flags=re.IGNORECASE)
        return template

    def brand_template(self, title, template):
        template = re.sub("\\bTEMPLATE_NAME\\b", title, template)
        return template
