import xml.etree.ElementTree as eT
from dataclasses import dataclass, field
from pathlib import Path

from joystick_diagrams.input.axis import Axis, AxisDirection
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.profile_collection import ProfileCollection

AXIS_TO_AXIS_TYPES = {
    "R-Axis X-": Axis(AxisDirection.RX),
    "R-Axis X+": Axis(AxisDirection.RX),
    "L-Axis X": Axis(AxisDirection.X),
    "L-Axis Y": Axis(AxisDirection.Y),
    "R-Axis Z-": Axis(AxisDirection.RZ),
    "R-Axis Z+": Axis(AxisDirection.RZ),
}

HAT_DIR_TO_DIR = {
    "Up": HatDirection.U,
    "Up_Right": HatDirection.UR,
    "Right": HatDirection.R,
    "Down_Right": HatDirection.DR,
    "Down": HatDirection.D,
    "Down_Left": HatDirection.DL,
    "Left": HatDirection.L,
    "Up_Left": HatDirection.UL,
}

default_profile_name = "Default"


@dataclass
class Parser:
    path: str
    data: list = field(init=False, default_factory=list)

    def run(self):
        folders = Path(self.path).iterdir()

        pc = ProfileCollection()
        pc.create_profile(default_profile_name)

        xml_files = check_folders(folders)

        for xml in xml_files:
            process_xml_file(xml, pc)

        return pc

    def handle_valid_file(self, file):
        self.data.append(file)


def process_xml_file(file: Path, profile_collection: ProfileCollection):
    with open(file, "r") as f:
        total_lines = f.readlines()

        xml = eT.fromstringlist(
            [line for count, line in enumerate(total_lines) if count not in [1, 2]]
        )

    process_device(xml, profile_collection)


def process_device(device_xml: eT.Element, collection: ProfileCollection):
    device_name = device_xml.get("DeviceName")
    device_guid = device_xml.get("GUID")

    if (device_name or device_guid) is None:
        return

    profile = collection.get_profile(default_profile_name)

    dev = profile.add_device(device_guid, device_name)  # type: ignore

    contexts = device_xml.findall("Context")

    controls = process_contexts(contexts)

    for control in controls:
        # Check if we have an existing input for the device
        existing_input = dev.get_input(
            dev.resolve_type(control.base_control), control.base_control.identifier
        )

        # Update the command to prevent overwrite
        if existing_input and not control.modifiers:
            existing_input.command = f"{existing_input.command} | {control.action}"

        # Handle modifiers being added to existing controls (where we have overlapping base)
        if existing_input and control.modifiers:
            existing_input.add_modifier(
                {x.identifier for x in control.modifiers}, control.action
            )
        elif control.modifiers:
            dev.add_modifier_to_input(
                control.base_control,
                {x.identifier for x in control.modifiers},
                control.action,
            )
        else:
            dev.create_input(control.base_control, control.action)


def process_contexts(contexts: list[eT.Element]) -> list["Control"]:
    controls = []
    for context in contexts:
        # context_name = context.get("ContextName")

        actions = context.findall("Action")

        # Multiple contexts can be linked, i.e. X- and X+ are just X
        for action in actions:
            if action.get("ActionName") is None:
                continue

            action_name = split_action_name(action.get("ActionName"))  # type: ignore

            primary_action_keys = action.find("Primary").findall(
                "KEY"
            )  # TODO could fail

            if primary_action_keys:
                control, modifiers = process_action_keys(primary_action_keys)

                if control and modifiers is None:
                    continue

                controls.append(Control(action_name, control, modifiers))

    return controls


def process_action_keys(keys: list[eT.Element]) -> tuple:
    if not keys:
        return (None, None)

    if len(keys) == 1:
        ctrl = parse_joystick_bind_information(keys[0].get("Information"))
        return (ctrl, {})
    else:
        controls = list()
        for key in keys:
            controls.append(parse_joystick_bind_information(key.get("Information")))

        if controls:
            main_control = controls.pop(0)

            return (main_control, controls)

        return (None, None)


def parse_joystick_bind_information(bind_information: str):
    """Process the particular bind key from information block.

    The data here is inconsistent from FS2020, so proceeding cautiously"""
    data = bind_information.replace("Joystick", "").strip()

    parts = data.split(" ")

    if len(parts) != 2:
        print("Error with expected parts")

    match parts[0]:
        case "Button":
            return Button(int(parts[1]))
        case "Pov":
            return Hat(1, HAT_DIR_TO_DIR[parts[1]])
        case "L-Axis":
            return AXIS_TO_AXIS_TYPES[data]
        case "R-Axis":
            return AXIS_TO_AXIS_TYPES[data]
        case _:
            print(f"Unexpected control type {parts[1]}")


def split_action_name(name_key: str):
    splits = [x for x in name_key.split("_") if x not in ["KEY", "AXIS"]]
    return " ".join(splits).title()


def file_check(file):
    with open(file, "rb") as b:
        if b.read(5) == b"<?xml":
            return True
    return False


def check_folders(folders):
    valid_files = []
    for folder in folders:
        if not folder.is_dir():
            continue

        for file in folder.iterdir():
            valid_files.append(file) if file_check(file) else None

    return valid_files


@dataclass
class Control:
    action: str
    base_control: Button | Axis | Hat
    modifiers: list[Button | Axis | Hat]

    def __repr__(self):
        return f"{self.action} | {self.base_control} | {id(self.base_control)}"


if __name__ == "__main__":
    ps = Parser(
        r"C:\Users\RCox\AppData\Local\Packages\Microsoft.FlightSimulator_8wekyb3d8bbwe\SystemAppData\wgs\00090000038358E7_00000000000000000000000069F80140"
    )
    data = ps.run()

    print(data)
