import logging
from copy import deepcopy

from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugin_manager import ParserPluginManager, PluginInterface

_logger = logging.getLogger(__name__)


class appState:
    """

    appState for managing shared data for application.

    """

    _inst = None

    def __new__(cls, *args, **kwargs):
        if not cls._inst:
            cls._inst = super(appState, cls).__new__(cls, *args, **kwargs)
            cls._inst._init()
        return cls._inst

    def _init(self) -> None:
        self.plugin_manager: ParserPluginManager | None = None
        self.raw_profiles: list = self.profile_mock()
        self.profileObjectMapping = {x.name: x for x in self.raw_profiles}
        self.profileParentMapping: dict[str, list[str]] = {
            "profile1": ["profile2", "profile3"],
            "profile2": [],
            "profile3": [],
        }  # TODO correctly initialise these
        self.processedProfileObjectMapping: dict[str, Profile_] = {}  # TODO Think here about name colissions

    def init_plugins(self, plugin_manager: ParserPluginManager):
        self.plugin_manager = plugin_manager

    def update_parent_profile_map(self, key: str, values: list):
        self.profileParentMapping[key] = values

    def update_procssed_profiles(self):
        for profile, parents in self.profileParentMapping.items():
            profile_copy = deepcopy(self.profileObjectMapping[profile])

            if not parents:
                self.processedProfileObjectMapping[profile] = profile_copy
                continue

            if parents:
                parents.reverse()
                merged_profiles = self.profileObjectMapping[parents[0]]

                for parent in parents[:1]:
                    obj = self.profileObjectMapping[parent]
                    merged_profiles = merged_profiles.merge_profiles(obj)

            self.processedProfileObjectMapping[profile] = merged_profiles.merge_profiles(profile_copy)

    def profile_mock(self):
        collection1 = ProfileCollection()
        profile1 = collection1.create_profile("Profile1")

        dev1 = profile1.add_device("dev_1", "dev_1")
        dev2 = profile1.add_device("dev_2", "dev_2")

        dev1.create_input("input1", "shoot")
        dev2.create_input("input2", "fly")

        dev1.add_modifier_to_input("input1", {"ctrl"}, "bang")
        dev1.add_modifier_to_input("input1", {"alt"}, "bang again")

        collection2 = ProfileCollection()
        profile2 = collection2.create_profile("Profile2")

        dev3 = profile2.add_device("dev_1", "dev_1")
        dev4 = profile2.add_device("dev_2", "dev_2")

        dev3.create_input("input1", "potato")

        dev3.add_modifier_to_input("input1", {"ctrl"}, "hello")
        dev1.add_modifier_to_input("input1", {"ctrl", "alt", "space"}, "bang again again")

        dev4.create_input("input4", "another")

        collection3 = ProfileCollection()
        profile3 = collection3.create_profile("Profile3")

        dev3 = profile3.add_device("dev_3", "dev_3")
        dev4 = profile3.add_device("dev_4", "dev_4")

        dev3.create_input("input100", "potato")

        dev3.add_modifier_to_input("input100", {"ctrl"}, "input 100 modifier")

        dev4.create_input("input4 dev4", "dev4input4")

        return [profile1, profile2, profile3]


if __name__ == "__main__":
    _appState = appState()

    _appState.update_procssed_profiles()
    print(_appState)

    # profile1.merge_profiles(profile2)
