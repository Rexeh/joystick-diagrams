import unittest

import joystick_diagrams.adaptors.dcs.dcs_world as dcs


def setup_function():
    dd_device("dev-1", "device 1")
    add_device("dev-2", "device 2")


def inputs_no_modifiers():
    pass
