import logging

from joystick_diagrams.input.profile import Profile_

_logger = logging.getLogger("__name__")


class ProfileCollection:
    """Contains profiles for grouping devices and their input functionality"""

    def __init__(self):
        self.profiles: dict[str, Profile_] = {}

    def create_profile(self, profile_name: str) -> Profile_:
        profile_name = profile_name.lower()

        if self.get_profile(profile_name) is None:
            self.profiles[profile_name] = Profile_(profile_name)

        return self.profiles.get(profile_name)  # type: ignore

    def get_profile(self, profile_name) -> Profile_ | None:
        return self.profiles.get(profile_name.lower())


# Profile Collection
#   -> Profile
#       -> Device
#           -> Input
#               -> Command
#               -> Modifiers
#                   -> Command

if __name__ == "__main__":
    collection = ProfileCollection()

    inst1 = collection.create_profile("test")
    inst2 = collection.create_profile("abc")

    dev1 = inst1.add_device("guid1", "joystick_1")
    dev2 = inst1.add_device("guid2", "joystick_2")

    if dev1 is not None:
        print(dev1.inputs)
