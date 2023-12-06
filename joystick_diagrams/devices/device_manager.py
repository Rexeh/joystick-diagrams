import logging
from time import sleep
from typing import Any

from joystick_diagrams.devices import dill

_LOGGER = logging.getLogger(__name__)
_ACTIVE_DEViCES = {}

# Action mappings for device changes
DEVICE_ACTIONS = {1: "DEVICE_ADDED", 2: "DEVICE_REMOVED"}

_device_changes = []


# Cannot debug?
def _update_device_register(data: dill._DeviceSummary, action):
    _LOGGER.info(f"Device was altered, added to device changes")
    _device_changes.append([dill.DeviceSummary(data), action])


dill.DILL.set_device_change_callback(_update_device_register)  # Figure out this callable


# CAN BE DEBUGGED
def process_device_changes():
    if len(_device_changes) == 0:
        return

    for changes in _device_changes:
        device, action = changes.pop(0)
        _LOGGER.info(f"Device was changed: {device.__repr__}")
        _LOGGER.info(f"Device was : {DEVICE_ACTIONS[action]}")


def run():
    # Setup initial devices
    while True:
        _LOGGER.info(f"Devices {dill.DILL.get_device_count()}")
        process_device_changes()
        sleep(1)


if __name__ == "__main__":
    lst = [1, 2, 3, 4, 5]

    while len(lst) != 0:
        i = lst.pop(0)
        print(f"Popped {i}")

    print("finished")
