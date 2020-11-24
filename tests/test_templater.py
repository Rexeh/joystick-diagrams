import os
import unittest
from io import BytesIO
from pathlib import Path

from lxml import etree
from xml.etree import ElementTree

from classes.templater import Templater


class TestTemplater(unittest.TestCase):

    def test_templater(self):
        templater = Templater(Path(os.path.join('templates', 'CH Fighterstick USB.svg')))
        templater.replace_with_bindings({})
        template_as_bytes = templater.get_template_as_bytes()
        assert template_as_bytes
        tree = etree.parse(BytesIO(template_as_bytes))
        button_rect = self.get_element_by_id('Button_13_rect', tree)
        assert button_rect.attrib['fill'] == '#ffffff'
        button_text = self.get_element_by_id('Button_13_text', tree)
        assert button_text.text == 'Unbound'

    def test_templater_with_bindings(self):
        templater = Templater(Path(os.path.join('templates', 'CH Fighterstick USB.svg')))
        templater.replace_with_bindings({'Button_13': 'Turbo Boost'})
        template_as_bytes = templater.get_template_as_bytes()
        assert template_as_bytes
        tree = etree.parse(BytesIO(template_as_bytes))
        button_text = self.get_element_by_id('Button_13_div', tree)
        assert button_text.text == 'Turbo Boost'

    def get_element_by_id(self, element_id: str, tree: ElementTree):
        return tree.xpath(f"//*[@id='{element_id}']")[0]
