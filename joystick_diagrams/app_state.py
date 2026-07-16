import logging
from copy import deepcopy

from PySide6.QtCore import QTimer

from joystick_diagrams.conflict_strategy import (
    AliasConflictStrategy,
    apply_input_conflict,
    get_alias_strategy,
)
from joystick_diagrams.db.device_alias_service import DeviceAliasService
from joystick_diagrams.db.device_service import DeviceService
from joystick_diagrams.db.label_service import LabelService
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.profile import Profile_
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.input_routing import apply_routes, union_profile_routes
from joystick_diagrams.plugin_wrapper import PluginWrapper
from joystick_diagrams.plugins.output_plugin_manager import OutputPluginManager
from joystick_diagrams.plugins.plugin_manager import ParserPluginManager
from joystick_diagrams.profile_wrapper import ProfileWrapper

_logger = logging.getLogger(__name__)


class AppState:
    """appState for managing shared data for application."""

    _inst = None

    def __new__(cls, *args, **kwargs):
        if not cls._inst:
            cls._inst = super(AppState, cls).__new__(cls)

            cls._inst._init(
                plugin_manager=kwargs["plugin_manager"],
                output_plugin_manager=kwargs.get("output_plugin_manager"),
            )
        return cls._inst

    def _init(
        self,
        plugin_manager: ParserPluginManager,
        output_plugin_manager: OutputPluginManager | None = None,
    ) -> None:
        self.plugin_manager: ParserPluginManager = plugin_manager
        self.output_plugin_manager: OutputPluginManager | None = output_plugin_manager

        self.main_window = None
        self.label_service = LabelService()
        self.device_service = DeviceService()
        self.device_alias_service = DeviceAliasService()
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

        # Initialise wrappers — restores state, resolves inheritance from parents
        # Must run before aliasing so inheritance uses original (unaliased) profiles,
        # and aliasing then resolves GUIDs on the final merged result.
        self.initialise_profile_wrappers()

        # Apply cross-device input routes (e.g. Gremlin vJoy remaps) so that
        # commands bound to the remap target land on the correct physical input
        # before alias resolution collapses device GUIDs.
        self._apply_input_routes(self.profile_wrappers, strategy=get_alias_strategy())

        # Apply GUID alias resolution on fully inherited profiles
        self._apply_guid_aliases()

    def reprocess_profiles_with_notice(
        self, message: str = "Settings applied — profiles reprocessed"
    ) -> None:
        """Rebuild profile wrappers + surface a status-bar toast + invalidate
        cached data pages so they rebuild on next visit.

        Intended for UI handlers that mutate a *process-time* setting
        (alias/inheritance strategy, plugin enable/disable, …) and need the
        merged profile state refreshed. Safe to call when no plugins have
        been run yet — the pipeline short-circuits to empty state.
        """
        self.process_profiles_from_collections()
        if self.main_window is None:
            return
        try:
            self._flash_status_label(message, 3000)
        except (AttributeError, RuntimeError) as e:
            _logger.debug(f"Could not flash status label: {e}")
        try:
            self.main_window._invalidate_data_pages()
        except (AttributeError, RuntimeError) as e:
            _logger.debug(f"Could not invalidate data pages: {e}")

    def _flash_status_label(self, message: str, duration_ms: int) -> None:
        """Temporarily replace main_window.statusLabel text with `message`.

        The existing status-label text is restored after `duration_ms`. We
        use the statusLabel instead of statusBar().showMessage() because the
        main window adds two permanent widgets with stretch=1 to the status
        bar, which crowd out the temporary-message area.
        """
        label = self.main_window.statusLabel
        previous = label.text()
        label.setText(message)
        QTimer.singleShot(duration_ms, lambda: _restore_status_label(label, previous))

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

    @staticmethod
    def _apply_input_routes(
        profile_wrappers: list["ProfileWrapper"],
        strategy: AliasConflictStrategy,
    ) -> None:
        """Apply cross-device input routes across all profile wrappers.

        Routes (populated by plugins such as Joystick Gremlin) describe
        "commands bound to device A / input X should display on device B /
        input Y". Routes from all wrappers are unioned, then applied to every
        profile. Conflicts on the same destination input use the alias
        strategy (short/long/conditional flow through as the loser qualifier).
        """
        all_profiles = [w.profile for w in profile_wrappers if w.profile is not None]
        if not all_profiles:
            return

        union_routes = union_profile_routes(all_profiles)
        if not union_routes:
            return

        device_names = AppState._collect_device_names(all_profiles)

        for profile in all_profiles:
            apply_routes(profile, union_routes, strategy, device_names)

    @staticmethod
    def _collect_device_names(profiles: list[Profile_]) -> dict[str, str]:
        """Build a device_guid -> device_name lookup from all known profiles."""
        names: dict[str, str] = {}
        for profile in profiles:
            for guid, device in profile.devices.items():
                if guid not in names and device.name:
                    names[guid] = device.name
        return names

    def _apply_guid_aliases(self):
        """Apply device GUID alias resolution to all profile wrappers.

        Resolves aliased GUIDs so that devices with different physical GUIDs
        that represent the same logical device are merged under the canonical GUID.
        """
        if not self.device_alias_service.get_all_aliases():
            return

        for wrapper in self.profile_wrappers:
            wrapper.profile = self._apply_aliases_to_profile(
                wrapper.profile, self.device_alias_service
            )

    @staticmethod
    def _apply_aliases_to_profile(
        profile: Profile_,
        alias_service: DeviceAliasService,
        strategy: AliasConflictStrategy | None = None,
    ) -> Profile_:
        """Resolve GUID aliases within a single profile, merging devices as needed.

        For each canonical GUID, all aliased source devices and the target device
        (if present) are grouped together. The first source in iteration order
        becomes the canonical device's base (source-wins-primary). Subsequent
        sources and the target are merged in as losers; primary-binding conflicts
        are resolved per the configured `strategy` (defaults to the app-wide
        setting). Non-conflicting inputs gap-fill as before.

        Args:
            profile: The profile to process (mutated in place and returned).
            alias_service: Service providing GUID alias resolution.
            strategy: Override for the alias conflict strategy. None reads the
                user setting (via `get_alias_strategy()`).

        Returns:
            The profile with aliases resolved.
        """
        if strategy is None:
            strategy = get_alias_strategy()

        items = list(profile.devices.items())
        original_count = len(items)

        # Group devices by canonical GUID, preserving iteration order for sources.
        groups: dict[str, dict] = {}
        for guid, device in items:
            canonical = alias_service.resolve(guid)
            is_source = canonical != guid
            group = groups.setdefault(canonical, {"sources": [], "target": None})
            if is_source:
                group["sources"].append(device)
            else:
                group["target"] = device

        new_devices: dict[str, Device_] = {}
        for canonical, group in groups.items():
            sources = group["sources"]
            target = group["target"]

            if not sources:
                # No aliasing for this canonical - keep target as-is.
                new_devices[canonical] = target
                continue

            # First source wins primary. Subsequent sources and the target are losers.
            winner = deepcopy(sources[0])
            winner.guid = canonical

            losers: list[Device_] = list(sources[1:])
            if target is not None:
                losers.append(target)

            for loser in losers:
                _merge_alias_loser_into_winner(winner, loser, strategy)

            new_devices[canonical] = winner
            if canonical != sources[0].guid:
                _logger.debug(
                    f"Aliased device {sources[0].guid[:8]} -> {canonical[:8]} in profile {profile.name}"
                )

        _logger.debug(
            f"Alias resolution complete for {profile.name}: {original_count} devices -> {len(new_devices)} devices"
        )
        profile.devices = new_devices
        return profile

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


def _merge_alias_loser_into_winner(
    winner: Device_, loser: Device_, strategy: AliasConflictStrategy
) -> None:
    """Merge a losing (aliased) device's inputs into the winner in-place.

    Non-conflicting input keys are copied wholesale. Conflicts are resolved per
    `strategy`; loser qualifier for promoted modifiers is the loser's device name.
    """
    for input_type, inputs in loser.inputs.items():
        for input_key, loser_input in inputs.items():
            if input_key not in winner.inputs[input_type]:
                winner.inputs[input_type][input_key] = deepcopy(loser_input)
            else:
                apply_input_conflict(
                    winner=winner.inputs[input_type][input_key],
                    loser=loser_input,
                    loser_qualifier=loser.name,
                    strategy=strategy,
                )


def _restore_status_label(label, previous_text: str) -> None:
    """QTimer callback: restore the prior statusLabel text.

    Defensive against the label being torn down before the timer fires
    (e.g. window closed mid-flash) — RuntimeError from PySide is swallowed.
    """
    try:
        label.setText(previous_text)
    except RuntimeError:
        pass


if __name__ == "__main__":
    pass
