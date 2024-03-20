import json
from pathlib import Path

from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input.profile_collection import ProfileCollection

POV_INT_TO_DIR = {
    0: HatDirection.U,
    4500: HatDirection.UR,
    9000: HatDirection.R,
    13500: HatDirection.DR,
    18000: HatDirection.D,
    22500: HatDirection.DL,
    27000: HatDirection.L,
    31500: HatDirection.UL,
}


class XRNeckSafer:
    def __init__(self, config_file_path: Path):
        self.path = self.validate_xr_file(config_file_path)
        self.collection = ProfileCollection()

    def validate_xr_file(self, path: Path):
        # TODO Extend validation

        self.data = json.loads(path.read_text())
        return Path(path)

    def process_file(self):
        actions = self.data["ActionProperties"]

        profile = self.collection.create_profile("Default")
        # Final Name is Action.ID + Event.Name
        for action in actions:
            action_name: str = action.get("Id")
            print(f"Action name is : {action_name}")

            for event in action.get("Events"):
                # Each EVENT has an Event Name
                event_name = event.get("Name")

                joined_name = f"{action_name} - {event_name}"

                # Each Event has 1 or more InputCombinations
                input_combinations = event.get("InputCombinations")

                # Get the input combinations
                for combination in input_combinations:
                    # Each Input Combination can have 1 or More joystick buttons
                    # If multiple keys are pressed it  creates multiple joystick buttons
                    joystick_buttons = combination.get("JoystickButtons")

                    if not joystick_buttons:
                        continue

                    # print(f"Combination has joystick controls - {joystick_controls}")
                    self.create_joystick_inputs(joystick_buttons, profile, joined_name)

                # print(f"Inputs are: {input_combinations}")

        return self.collection

    def create_joystick_inputs(self, joysticks: list, profile: Profile_, action: str):
        print(f"Processing joysticks {joysticks}")

        # If we have one joystick button then its a button
        if len(joysticks) == 1:
            joystick = joysticks.pop()

            dev = profile.add_device(joystick.get("JoystickGuid"), "")

            # Process Normal Button

            dev.create_input(
                self.create_control(joystick.get("Button"), joystick.get("POV")), action
            )
            return

        # If we have multiple buttons
        self.process_multi_joystick(joysticks, profile, action)
        return

    def process_multi_joystick(self, joysticks: list, profile: Profile_, action):
        main_device = joysticks.pop(0)

        def devices_to_set(joysticks: list) -> set:
            return {
                self.create_control(x.get("Button"), x.get("POV")).identifier
                for x in joysticks
            }

        modifier_set = devices_to_set(joysticks)

        dev = profile.get_device(main_device.get("JoystickGuid"))

        if dev is None:
            dev = profile.add_device(main_device.get("JoystickGuid"), "")

        dev.add_modifier_to_input(
            self.create_control(main_device.get("Button"), main_device.get("POV")),
            modifier_set,
            action,
        )

    def create_control(self, button_value, pov_value):
        if pov_value == -1:
            return Button(button_value + 1)

        return Hat(pov_value + 1, POV_INT_TO_DIR[button_value])


if __name__ == "__main__":
    psr = XRNeckSafer(Path(r"C:\ProgramData\XRNeckSafer\XRNeckSafer.cfg"))

    col = psr.process_file()

    print(col)
