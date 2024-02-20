"""Serves as a wrapper around Plugin Profiles, allowing customisation and restored state of profiles"""

from copy import deepcopy

from joystick_diagrams import app_state
from joystick_diagrams.db import db_profile_parents, db_profiles
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.plugin_wrapper import PluginWrapper


class ProfileWrapper:
    def __init__(self, profile: Profile_, origin: PluginWrapper):
        # Reference items
        self.original_profile: Profile_ = profile
        self.profile_origin: PluginWrapper = origin

        # Extensions
        self.parents: list[ProfileWrapper] = []
        self.display_name: str = ""

        # Master profile which represents a fully built version of the base
        self.profile: Profile_ = deepcopy(self.original_profile)
        # self.errors: list[str] = []

    def __repr__(self) -> str:
        return (
            f"Profile Wrapper: {self.original_profile.name} from {self.profile_origin}"
        )

    def initialise_wrapper(self):
        """Initalises the wrapper, applying the app settings on top of the profile object

        Results in a fully completed profile, and initalised ProfileWrapper with any relevant settings restored from DB"""
        self.get_profile_settings()
        self.get_parents_for_profile()
        self.inherit_parents_into_profile()

    def get_parents_for_profile(self):
        """Try get the parents for a given profile from persisted state"""
        self.parents.clear()
        parents = db_profiles.get_profile_parents(self.profile_key)
        _state = app_state.AppState()
        for parent_key in parents:
            _wrapper = [
                x for x in _state.profile_wrappers if x.profile_key == parent_key
            ]

            if _wrapper:
                self.parents.append(_wrapper[0])

    def update_parents_for_profile(self, parents: list["ProfileWrapper"]):
        keys = [x.profile_key for x in parents]
        db_profile_parents.add_parents_to_profile(self.profile_key, keys)
        self.parents = parents
        self.inherit_parents_into_profile()

    def inherit_parents_into_profile(self):
        if not self.parents:
            return

        _parents = self.parents  # Reverse list to flip obj >> parent
        _parents.reverse()

        merged_profiles = deepcopy(self.original_profile)

        for parent in _parents[:1]:
            obj = deepcopy(parent.original_profile)
            merged_profiles = merged_profiles.merge_profiles(obj)

        self.profile = merged_profiles

    def get_profile_settings(self):
        """Gets the profile settings if available

        Uses original profile name, and origin as composite key
        """
        profile_settings = db_profiles.get_profile(self.profile_key)

        if profile_settings:
            # TODO restore settings
            pass

    @property
    def profile_name(self):
        """Returns the name to be used to respresent the profile"""
        return (
            self.display_name.capitalize()
            if self.display_name
            else self.original_profile.name.capitalize()
        )

    @property
    def profile_key(self):
        """Returns the profile key used to uniquely identify it"""
        return f"{self.profile_origin.name.lower().strip()}_{self.original_profile.name.lower().strip()}"


if __name__ == "__main__":
    prof = Profile_("Test")

    print(dict(prof))
