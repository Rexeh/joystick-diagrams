import logging

from joystick_diagrams.profile.profile import Profile_

_logger = logging.getLogger("__name__")


class ProfileCollection:
    """ProfileCollection is the primary exchange format between ParserPlugins and the Main Application

    Groups PROFILE objects which comprise of other Input objects

    """

    def __init__(self):
        self.profiles: dict[str, Profile_] = {}

    def create_profile(self, profile_name: str) -> Profile_:
        profile_name = profile_name.lower()

        if self.get_profile(profile_name) is None:
            self.profiles[profile_name] = Profile_(profile_name)

        return self.profiles.get(profile_name)  # type: ignore

    def get_profile(self, profile_name) -> Profile_ | None:
        return self.profiles.get(profile_name.lower())

    def __len__(self):
        return len(self.profiles)


if __name__ == "__main__":
    pass
