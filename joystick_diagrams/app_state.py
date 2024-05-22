import logging

from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.plugins.plugin_manager import ParserPluginManager
from joystick_diagrams.profile.profile import Profile_
from joystick_diagrams.profile.profile_collection import ProfileCollection
from joystick_diagrams.profile_wrapper import ProfileWrapper

_logger = logging.getLogger(__name__)


class AppState:
    """appState for managing shared data for application."""

    _inst = None

    def __new__(cls, *args, **kwargs):
        if not cls._inst:
            cls._inst = super(AppState, cls).__new__(cls)

            cls._inst._init(plugin_manager=kwargs["plugin_manager"])
        return cls._inst

    def _init(self, plugin_manager: ParserPluginManager) -> None:
        self.plugin_manager: ParserPluginManager = plugin_manager

        self.main_window = None
        # Profile map for Plugin Profiles for lookups
        self.plugin_profile_map: dict[str, Profile_] = {}

        # Profile wrappers for use by app
        self.profile_wrappers: list[ProfileWrapper] = []

        self.profileParentMapping: dict[str, list[str]] = {}
        self.processedProfileObjectMapping: dict[str, Profile_] = {}
        self.process_profiles_from_collections()

    def process_profiles_from_collections(self):
        plugin_collections = self.get_plugin_wrapper_collections()

        # Create profile map from raw profiles
        _logger.debug(
            f"Processing profiles from plugins with {len(plugin_collections)} plugin collections"
        )
        self.create_plugin_profile_map(plugin_collections)

        # Create profile wrappers for use in app
        self.create_profile_wrappers(self.plugin_manager.get_enabled_plugin_wrappers())

        # Initialise wrappers / restoring state and customisation
        self.initialise_profile_wrappers()

    def initialise_profile_wrappers(self):
        _logger.debug(f"Initialising {len(self.profile_wrappers)} profile wrappers ")

        for wrapper in self.profile_wrappers:
            wrapper.initialise_wrapper()

    def create_profile_wrappers(self, plugin_wrappers: list[PluginWrapper]):
        # Clear Existing Wrappers
        self.profile_wrappers.clear()

        for plugin in plugin_wrappers:
            # Get pluugins only

            if not plugin.plugin_profile_collection:
                continue

            profiles = plugin.plugin_profile_collection.profiles

            _logger.debug(f"{len(profiles)} profiles detected for {plugin}")

            for profile in profiles.values():
                self.profile_wrappers.append(ProfileWrapper(profile, plugin))

            _logger.debug(
                f"Processing profiles from plugins with {plugin} plugin collections"
            )

    def get_plugin_wrapper_collections(self) -> dict[str, ProfileCollection]:
        """Returns a list of Profile Collections that are tagged with the Plugin Name where the plugin is enabled"""
        return {
            x.name: x.plugin_profile_collection
            for x in self.plugin_manager.plugin_wrappers
            if x.enabled and x.plugin_profile_collection
        }

    def create_plugin_profile_map(
        self, profile_collections: dict[str, ProfileCollection]
    ):
        """Processes the **raw** profilee collections from all loaded and enabled plugins, into a new dictionary mapping

        Key = Plugin Name - Profile Name
        Value = Profile Object

        The keys are used to denote profiles from different sources potentially with the same name
        """

        # Clear existing processed profiles
        self.plugin_profile_map.clear()

        for profile_source, profiles in profile_collections.items():
            for profile_obj in profiles.profiles.values():
                composite_key = f"{profile_source.lower().strip()}_{profile_obj.name.lower().strip()}"
                self.plugin_profile_map[composite_key] = profile_obj

        _logger.debug(
            f"Loaded plugins resulted in the following profiles being detected {self.plugin_profile_map}"
        )


if __name__ == "__main__":
    pass
