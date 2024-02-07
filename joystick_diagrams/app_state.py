import logging
from copy import deepcopy

from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugin_manager import ParserPluginManager

_logger = logging.getLogger(__name__)


class AppState:
    """appState for managing shared data for application."""

    _inst = None

    def __new__(cls, *args, **kwargs):
        if not cls._inst:
            cls._inst = super(AppState, cls).__new__(cls, *args, **kwargs)
            cls._inst._init()
        return cls._inst

    def _init(self) -> None:
        self.plugin_manager: ParserPluginManager | None = None
        self.profileObjectMapping: dict[str, Profile_] = {}
        self.profileParentMapping: dict[str, list[str]] = {}  # TODO correctly initialise these
        self.processedProfileObjectMapping: dict[str, Profile_] = {}  # TODO Think here about name colissions
        self.update_processed_profiles()

    def init_plugins(self, plugin_manager: ParserPluginManager):
        """Injects a plugin manager instance to be managed by AppState"""
        self.plugin_manager = plugin_manager
        self.process_profile_collection_updates()

    ## Temp code for handling Plugin Wrapper changes > TODO REFACTOR
    def process_profile_collection_updates(self):
        self.process_loaded_plugins(self.get_plugin_wrapper_collections())

    def get_plugin_wrapper_collections(self) -> dict[str, ProfileCollection]:
        """Returns a list of Profile Collections that are tagged with the Plugin Name where the plugin is enabled"""
        return {
            x.name: x.plugin_profile_collection
            for x in self.plugin_manager.plugin_wrappers
            if x.enabled and x.plugin_profile_collection
        }

    def process_loaded_plugins(self, profile_collections: dict[str, ProfileCollection]):
        """Processes the **raw** profilee collections from all loaded and enabled plugins, into a new dictionary mapping

        Key = Plugin Name - Profile Name
        Value = Profile Object

        The keys are used to denote profiles from different sources potentially with the same name
        """

        # Clear existing processed profiles
        self.profileObjectMapping.clear()

        for profile_source, profiles in profile_collections.items():
            for profile_name, profile_obj in profiles.profiles.items():
                combined_name = f"{profile_source} - {profile_name}"
                self.profileObjectMapping[combined_name] = profile_obj

        _logger.debug(f"Loaded plugins resulted in the following profiles being detected {self.profileObjectMapping}")

        self.update_processed_profiles()

    def get_processed_profile(self, profile_identifier: str) -> Profile_:
        """Return inherited profile for given Profile Identifier."""
        return self.processedProfileObjectMapping[profile_identifier]

    def get_processed_profiles(self) -> dict[str, Profile_]:
        """Return all inherited profiles."""
        return self.processedProfileObjectMapping

    def update_parent_profile_map(self, key: str, values: list) -> None:
        """Updates the global map of Profiles -> Profile Parents. Parents form the basis for inheritance of profiles.

        Returns None

        """
        self.profileParentMapping[key] = values
        self.update_processed_profiles()

    def update_processed_profiles(self) -> None:
        """Applies any PARENT relationships on top of profiles"""
        for profile_key, profile_obj in self.profileObjectMapping.items():
            self.processedProfileObjectMapping[profile_key] = deepcopy(profile_obj)

        for profile, parents in self.profileParentMapping.items():
            profile_copy = deepcopy(self.profileObjectMapping[profile])

            if not parents:
                self.processedProfileObjectMapping[profile] = profile_copy
                continue

            if parents:
                parents.reverse()  # Reverse list to flip obj >> parent
                merged_profiles = deepcopy(self.profileObjectMapping[parents[0]])

                for parent in parents[:1]:
                    obj = deepcopy(self.profileObjectMapping[parent])
                    merged_profiles = merged_profiles.merge_profiles(obj)

            self.processedProfileObjectMapping[profile] = merged_profiles.merge_profiles(profile_copy)
        _logger.debug(f"Updated processed profiles {self.processedProfileObjectMapping}")


if __name__ == "__main__":
    pass
