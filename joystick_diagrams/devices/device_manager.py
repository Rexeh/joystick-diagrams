import logging
from time import sleep

from joystick_diagrams.devices import dill

_LOGGER = logging.getLogger(__name__)
_ACTIVE_DEViCES: dict[str, object] = {}  # GUID : Display Name

# Action mappings for device changes
DEVICE_ACTIONS = {1: "DEVICE_ADDED", 2: "DEVICE_REMOVED"}

_device_changes = []


# Cannot debug?
def _update_device_register(data: dill._DeviceSummary, action):
    _LOGGER.info(f"Device {data} was altered, added to device changes")
    device_obj = dill.DeviceSummary(data)
    _device_changes.append(device_obj)


dill.DILL.set_device_change_callback(_update_device_register)  # mypy: ignore


# CAN BE DEBUGGED
def process_device_changes():
    if len(_device_changes) == 0:
        return

    for device in _device_changes:
        _LOGGER.info(f"Device was changed: {device.__repr__}")

        if not _ACTIVE_DEViCES.get(device.device_guid.uuid):
            _LOGGER.info(f"Device added to database: {device}")
            _ACTIVE_DEViCES[device.device_guid.uuid] = device
    print(f"Active Devices: {_ACTIVE_DEViCES}")
    _device_changes.clear()


def run():
    # Setup initial devices
    while True:
        _LOGGER.info(f"Devices {dill.DILL.get_device_count()}")
        process_device_changes()
        sleep(5)


if __name__ == "__main__":
    run()
