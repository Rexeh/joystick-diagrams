from pathlib import Path
from typing import Union, Any
from lxml import etree

Bindings = dict[str, str]


# TODO: templater should use xml id attributes
class Templater:
    _device_template_path: str
    _tree: etree.ElementTree
    _no_bind_text: str
    _brand_template: str

    def __init__(self, device_template_path: Union[str, Path], no_bind_text="Unbound", brand_template: str = ''):
        self._device_template_path = str(device_template_path)
        self._tree = etree.parse(str(device_template_path))
        self._no_bind_text = no_bind_text
        # TODO: should be parameterized and use the id of the button itself
        self._element_finder = etree.XPath(
            f"/svg:svg/svg:g/svg:g/svg:switch/svg:foreignObject/xhtml:div/xhtml:div/xhtml:div",
            namespaces={
                'svg': 'http://www.w3.org/2000/svg',
                'xhtml': 'http://www.w3.org/1999/xhtml'
            }
        )
        self._brand_template = brand_template

    def replace_with_bindings(self, items: Bindings) -> None:
        elements = self._element_finder(self._tree)
        for element in elements:
            element_name = element.text.strip()
            if element_name in ['Created by Joystick Diagrams', 'JOYSTICK NAME']:
                continue
            if element_name == "TEMPLATE_NAME":
                element.text = self._device_template_path
                continue
            element.text = items.get(element_name, self._no_bind_text)
            text_element = element.getparent().getparent().getparent().getnext()
            text_element.text = items.get(element_name, self._no_bind_text)

    def get_template_as_bytes(self) -> bytes:
        return etree.tostring(self._tree)
