"""
  This script can be used to add id attributes which will be pulled by the visualizer
"""
import os, sys

from lxml import etree


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def add_ids(file: str):
    print(f"add ids to {file}")
    tree = etree.parse(file)
    elements = tree.xpath(f"/svg:svg/svg:g/svg:g/svg:switch/svg:foreignObject/xhtml:div/xhtml:div/xhtml:div",
                          namespaces={
                              'svg': 'http://www.w3.org/2000/svg',
                              'xhtml': 'http://www.w3.org/1999/xhtml'
                          })
    for element in elements:
        element_name = element.text.strip()
        if element_name in ['Created by Joystick Diagrams']:
            continue
        # print(f"adding Id for {element_name}")
        element.attrib['id'] = f"{element_name}_div"
        text_element = element.getparent().getparent().getparent().getnext()
        text_element.attrib['id'] = f"{element_name}_text"
        rect_element = element.getparent().getparent().getparent().getparent().getparent().getprevious()
        rect_element.attrib['id'] = f"{element_name}_rect"

    print(f"saving {file}")
    tree.write(file)


def try_add_ids(file: str):
    try:
        add_ids(file)
    except:
        print(f"faulty template {file}", file=sys.stderr)


custom = os.listdir(path=f"templates{os.sep}Custom")
for file in custom:
    try_add_ids(f"templates{os.sep}Custom{os.sep}{file}")
user_submitted = os.listdir(path=f"templates{os.sep}User Submitted")
for file in user_submitted:
    try_add_ids(f"templates{os.sep}User Submitted{os.sep}{file}")
templates = os.listdir(path="templates")
for file in templates:
    if file in ["Custom", "User Submitted", "readme.md"]:
        continue
    try_add_ids(f"templates{os.sep}{file}")
