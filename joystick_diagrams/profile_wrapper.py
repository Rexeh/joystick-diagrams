"""Serves as a wrapper around Plugin Profiles, allowing customisation and restored state of profiles"""

import logging
import time
from copy import deepcopy

from joystick_diagrams.db import db_profile_parents, db_profiles
from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.profile.profile import Profile_

_logger = logging.getLogger(__name__)


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

        pt = time.perf_counter_ns()
        self.get_profile_settings()
        self.get_parents_for_profile()
        self.apply_device_settings()
        self.inherit_parents_into_profile()
        print(f"Wrapper init took {(time.perf_counter_ns()-pt)/1e+9}")

    def apply_device_settings(self):
        print(f"Applying device settings for {self.profile}")

        # Hide Devices
        filter_devices = [
            "0d54fae0-d151-11e9-8001-444553540000",
            "4ddcc6a0-3705-11ea-8001-444553540000",
            "0d54fae0-d151-11e9-8001-444553540000",
            "9026d510-cf53-11e9-8001-444553540000",
            "b3f41ad0-33e8-11ea-8003-444553540000",
        ]

        self.profile.devices = {
            g: o
            for g, o in self.profile.devices.items()
            if o.guid not in filter_devices
        }

        # Merge Devices

    def get_parents_for_profile(self):
        """Try get the parents for a given profile from persisted state"""
        self.parents.clear()
        parents = db_profiles.get_profile_parents(self.profile_key)

        _logger.debug(f"Parents for profile {self.profile_key} were {parents}")

        from joystick_diagrams.app_state import AppState  # TODO Resolve circular  dep

        _state = AppState()
        for parent_key, _ in parents:
            _logger.debug(f"Trying to get parent for {parent_key}")

            _wrapper = [
                x for x in _state.profile_wrappers if x.profile_key == parent_key
            ]
            _logger.debug(f"Profiles fond {_wrapper}")
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
        # profile_settings = db_profiles.get_profile(self.profile_key)

        return ...

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
    pass
