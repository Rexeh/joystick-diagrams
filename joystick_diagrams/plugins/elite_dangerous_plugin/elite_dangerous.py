"""Elite Dangerous XML Parser for use with Joystick Diagrams."""

import logging
import os
import uuid
from pathlib import Path
from typing import Union
from xml.dom import minidom

from joystick_diagrams.input.axis import Axis, AxisDirection
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.profile_collection import ProfileCollection

_logger = logging.getLogger(__name__)


class EliteDangerous:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.__load_file()
        self.devices = {}
        self.device_guid_map = {}  # Map device names to generated GUIDs

    def __load_file(self) -> str:
        if os.path.exists(self.file_path):
            if (os.path.splitext(self.file_path))[1] == ".binds":
                data = Path(self.file_path).read_text(encoding="utf-8")
                try:
                    self.__validate_file(data)
                except Exception as e:
                    raise Exception(
                        "File is not a valid Elite Dangerous XML"
                    ) from e
                else:
                    return data
            else:
                raise Exception(
                    "File must be a .binds file"
                )
        else:
            raise FileNotFoundError("File not found")

    def __validate_file(self, data) -> bool:
        try:
            parsed_xml = minidom.parseString(data)
        except ValueError as e:
            raise Exception(
                "File is not a valid Elite Dangerous XML"
            ) from e
        else:
            root = parsed_xml.documentElement
            if root.tagName == "Root" and root.hasAttribute("PresetName"):
                return True
            raise Exception("File is not a valid Elite Dangerous bindings file")

    def parse_file_data(self, data: str):
        return minidom.parseString(data)

    def get_device_guid(self, device_name: str) -> str:
        """Get or create a GUID for a device name."""
        if device_name not in self.device_guid_map:
            # Generate a consistent GUID based on device name
            self.device_guid_map[device_name] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ed-device-{device_name}"))
        return self.device_guid_map[device_name]

    def parse_binding_element(self, element) -> tuple[str, str] | None:
        """Parse a binding element (Primary, Secondary, or Binding) and return (device, key)."""
        device = element.getAttribute("Device")
        key = element.getAttribute("Key")

        if not device or not key or device == "{NoDevice}":
            return None

        return (device, key)

    def resolve_input(self, device_name: str, key: str) -> tuple[str, Union[Axis, Button, Hat, None]] | None:
        """Resolve a device/key combination to a device GUID and input control."""
        if not device_name or not key:
            return None

        device_guid = self.get_device_guid(device_name)
        input_control = self.parse_key(key)

        if not input_control:
            _logger.warning(f"Could not parse key: {key}")
            return None

        return (device_guid, input_control)

    def parse_key(self, key: str) -> Union[Axis, Button, Hat, None]:
        """Parse an Elite Dangerous key string into an input control."""
        key = key.strip()

        # Handle directional joystick axes (Pos_/Neg_ prefixes)
        if key.startswith(("Pos_Joy_", "Neg_Joy_")):
            # Extract the axis name (e.g., "Pos_Joy_RXAxis" -> "RXAxis")
            # Find where "Joy_" starts and take everything after it
            joy_start = key.find("Joy_") + 4  # Find "Joy_" and skip past it
            axis_name = key[joy_start:]

            if axis_name in ["XAxis", "YAxis", "ZAxis", "RZAxis", "RXAxis", "RYAxis"]:
                axis_map = {
                    "XAxis": "X",
                    "YAxis": "Y",
                    "ZAxis": "Z",
                    "RZAxis": "RZ",
                    "RXAxis": "RX",
                    "RYAxis": "RY"
                }
                return Axis(AxisDirection[axis_map[axis_name]])

        # Handle joystick inputs (regular axes, POV hats, buttons)
        elif key.startswith("Joy_"):
            axis_part = key[4:]  # Remove "Joy_" prefix

            # Handle regular axes
            if axis_part in ["XAxis", "YAxis", "ZAxis", "RZAxis", "RXAxis", "RYAxis"]:
                axis_map = {
                    "XAxis": "X",
                    "YAxis": "Y",
                    "ZAxis": "Z",
                    "RZAxis": "RZ",
                    "RXAxis": "RX",
                    "RYAxis": "RY"
                }
                return Axis(AxisDirection[axis_map[axis_part]])

            # Handle POV hats
            elif axis_part.startswith("POV") or "Hat" in axis_part:
                # Handle POV hats - simplified mapping
                hat_id = 1  # Default to hat 1
                if axis_part.endswith("Up"):
                    return Hat(hat_id, HatDirection.U)
                elif axis_part.endswith("Down"):
                    return Hat(hat_id, HatDirection.D)
                elif axis_part.endswith("Left"):
                    return Hat(hat_id, HatDirection.L)
                elif axis_part.endswith("Right"):
                    return Hat(hat_id, HatDirection.R)

        # Handle numbered joystick buttons (Joy_ followed by digits)
        if key.startswith("Joy_") and key[4:].isdigit():
            button_id = int(key[4:])
            return Button(button_id)

        # Handle keyboard keys
        elif key.startswith("Key_"):
            # For keyboard keys, we'll treat them as special buttons
            # This is a simplified approach - in a full implementation you might
            # want to handle keyboard separately or map to specific button IDs
            key_name = key[4:]
            # Map common keys to button IDs for consistency
            key_map = {
                "Space": 1,
                "Return": 2,
                "Escape": 3,
                "Tab": 4,
                "Backspace": 5,
                "LeftShift": 6,
                "LeftControl": 7,
                "LeftAlt": 8,
            }
            button_id = key_map.get(key_name, hash(key_name) % 1000 + 100)  # Fallback mapping
            return Button(button_id)

        # Handle mouse buttons
        elif key.startswith("Mouse_") and key[6:].isdigit():
            button_id = int(key[6:])
            return Button(button_id)

        # Handle mouse wheel (Z-axis) with direction
        elif key in ["Pos_Mouse_ZAxis", "Neg_Mouse_ZAxis"]:
            # Mouse wheel can be treated as a special axis or button
            # For simplicity, map to buttons (wheel up/down)
            if key == "Pos_Mouse_ZAxis":
                return Button(4)  # Mouse wheel up
            else:
                return Button(5)  # Mouse wheel down

        _logger.warning(f"Unrecognized key format: {key}")
        return None

    def get_human_readable_name(self, binding_name: str) -> str:
        """Convert binding names to human readable format."""
        # Custom friendly name mapping - add your XML node names here
        FRIENDLY_NAMES = {
            # Example mappings - replace with your preferred names
            "YawAxisRaw": "Yaw Axis",
            "RollAxisRaw": "Roll Axis",
            "PitchAxisRaw": "Pitch Axis",
            "LateralThrustRaw": "Lateral Thrust",
            "VerticalThrustRaw": "Vertical Thrust",
            "SetSpeed0" : "Throttle 0%",
            "SetSpeed25" : "Throttle 25%",
            "SetSpeed50" : "Throttle 50%",
            "SetSpeed75" : "Throttle 75%",
            "SetSpeed100" : "Throttle 100%",
            "ThrottleAxis": "Throttle",
            "ToggleReverseThrottleInput": "Reverse Throttle",
            "PrimaryFire": "Primary Fire",
            "SecondaryFire": "Secondary Fire",
            "UseBoostJuice": "Boost Engine",
            "Supercruise": "Supercruise",
            "Hyperspace": "Jump Drive",
            "HyperSuperCombination": "Supercruise / Jump",
            "ToggleFlightAssist": "Flight Assist",
            "LandingGearToggle": "Landing Gear",
            "CargoScoop": "Cargo Scoop",
            "DeployHardpointToggle" : "Deploy Hardpoints",
            "DeployHeatSink": "Heat Sink",
            "UseShieldCell": "Shield Cell",
            "FireChaffLauncher": "Chaff",
            "ChargeECM": "Charge ECM",
            "TriggerFieldNeutraliser": "Field Neutralizer",
            "SelectTarget": "Target",
            "CycleNextTarget": "Next Target",
            "CyclePreviousTarget": "Previous Target",
            "SelectHighestThreat": "Highest Threat",
            "WingNavLock": "Wing Nav Lock",
            "IncreaseEnginesPower": "Engine Power Up",
            "IncreaseWeaponsPower": "Weapon Power Up",
            "IncreaseSystemsPower": "System Power Up",
            "ResetPowerDistribution": "Reset Power",
            "UIFocus": "UI Focus",
            "GalaxyMapOpen": "Galaxy Map",
            "SystemMapOpen": "System Map",
            "HeadLookToggle": "Head Look",
            "CamPitchAxis": "Camera Pitch",
            "CamYawAxis": "Camera Yaw",
            "ToggleCargoScoop": "Cargo Scoop",
            "EjectAllCargo": "Eject Cargo",
            "MicrophoneMute": "Mute",
            "HMDReset": "HMD Reset",
            "Pause": "Pause",
            "FriendsMenu": "Friends",
            "OpenCodexGoToDiscovery": "Codex",
            "PlayerHUDModeToggle": "HUD Mode",
            "ExplorationFSSEnter": "FSS Scanner",
            "ExplorationFSSZoomIn"
            "ExplorationFSSCameraPitchDecrease": "FSS Camera Pitch Down",
            "ExplorationFSSCameraYaw": "FSS Camera Yaw",
            "ExplorationFSSCameraYawIncrease": "FSS Camera Yaw Up",
            "ExplorationFSSCameraYawDecrease": "FSS Camera Yaw Down",
            "ExplorationFSSZoomIn": "FSS Zoom In",
            "ExplorationFSSZoomOut": "FSS Zoom Out",
            "ExplorationFSSMiniZoomIn": "FSS Mini Zoom In",
            "ExplorationFSSMiniZoomOut": "FSS Mini Zoom Out",
            "ExplorationFSSRadioTuningX_Raw": "FSS Radio Tuning X",
            "ExplorationFSSRadioTuningY_Raw": "FSS Radio Tuning Y",
            "ExplorationFSSRadioTuningZ_Raw": "FSS Radio Tuning Z",
            "ExplorationFSSRadioTuningW_Raw": "FSS Radio Tuning W",
            "ExplorationFSSRadioTuningX_Raw": "FSS Radio Tuning X",
            "ExplorationFSSRadioTuningY_Raw": "FSS Radio Tuning Y",
            "ExplorationFSSRadioTuningZ_Raw": "FSS Radio Tuning Z",
            "ToggleButtonUpInput": "Toggle Button Up",
            "ToggleButtonDownInput": "Toggle Button Down",
            "ExplorationFSSShowHelp" : "FSS Help",
            "UI_Up": "UI Up",
            "UI_Down": "UI Down",
            "UI_Left": "UI Left",
            "UI_Right": "UI Right",
            "UI_Select": "UI Select",
            "UI_Back": "UI Back",
            "UI_Toggle": "UI Toggle",
            "CycleNextPanel": "Next Panel",
            "CyclePreviousPanel": "Previous Panel",
            "CycleNextPage": "Next Page",
            "CyclePreviousPage": "Previous Page",
            "MouseHeadlook": "Mouse Look",
            "HeadLookReset": "Reset Head Look",
            "HeadLookPitchUp": "Head Look Up",
            "HeadLookPitchDown": "Head Look Down",
            "HeadLookYawLeft": "Head Look Left",
            "HeadLookYawRight": "Head Look Right",
            "HeadLookPitchAxis": "Head Look Pitch",
            "HeadLookYawAxis": "Head Look Yaw",
            "MotionHeadlook": "Motion Look",
            "HeadLookPitchAxisRaw": "Head Pitch Axis",
            "HeadLookYawAxisRaw": "Head Yaw Axis",
            "CamTranslateYAxis": "Camera Up/Down",
            "CamTranslateForward": "Camera Forward",
            "CamTranslateBackward": "Camera Back",
            "CamTranslateXAxis": "Camera Left/Right",
            "CamTranslateLeft": "Camera Left",
            "CamTranslateRight": "Camera Right",
            "CamTranslateZAxis": "Camera Zoom",
            "CamTranslateUp": "Camera Up",
            "CamTranslateDown": "Camera Down",
            "CamZoomAxis": "Camera Zoom",
            "CamZoomIn": "Zoom In",
            "CamZoomOut": "Zoom Out",
            "CamTranslateZHold": "Camera Z Hold",
            "GalaxyMapHome": "Galaxy Map Home",
            "ToggleDriveAssist": "Drive Assist",
            "DriveAssistDefault": "Drive Assist Default",
            "SteeringAxis": "Steering",
            "SteerLeftButton": "Steer Left",
            "SteerRightButton": "Steer Right",
            "BuggyRollAxisRaw": "SRV Roll",
            "BuggyRollLeftButton": "SRV Roll Left",
            "BuggyRollRightButton": "SRV Roll Right",
            "BuggyPitchAxis": "SRV Pitch",
            "BuggyPitchUpButton": "SRV Pitch Up",
            "BuggyPitchDownButton": "SRV Pitch Down",
            "VerticalThrustersButton": "Vertical Thrusters",
            "BuggyPrimaryFireButton": "SRV Primary Fire",
            "BuggySecondaryFireButton": "SRV Secondary Fire",
            "AutoBreakBuggyButton": "SRV Auto Brake",
            "HeadlightsBuggyButton": "SRV Headlights",
            "ToggleBuggyTurretButton": "SRV Turret",
            "BuggyCycleFireGroupNext": "SRV Next Fire Group",
            "BuggyCycleFireGroupPrevious": "SRV Previous Fire Group",
            "SelectTarget_Buggy": "SRV Target",
            "BuggyTurretYawAxisRaw": "SRV Turret Yaw",
            "BuggyTurretYawLeftButton": "SRV Turret Left",
            "BuggyTurretYawRightButton": "SRV Turret Right",
            "BuggyTurretPitchAxisRaw": "SRV Turret Pitch",
            "BuggyTurretPitchUpButton": "SRV Turret Up",
            "BuggyTurretPitchDownButton": "SRV Turret Down",
            "BuggyTurretMouseSensitivity": "SRV Turret Mouse Sensitivity",
            "BuggyTurretMouseDeadzone": "SRV Turret Mouse Deadzone",
            "DriveSpeedAxis": "SRV Speed",
            "BuggyThrottleRange": "SRV Throttle Range",
            "BuggyToggleReverseThrottleInput": "SRV Reverse Throttle",
            "IncreaseSpeedButtonMax": "SRV Max Speed",
            "DecreaseSpeedButtonMax": "SRV Min Speed",
            "ToggleCargoScoop_Buggy": "SRV Cargo Scoop",
            "EjectAllCargo_Buggy": "SRV Eject Cargo",
            "RecallDismissShip": "Recall Ship",
            "UIFocus_Buggy": "SRV UI Focus",
            "FocusLeftPanel_Buggy": "SRV Left Panel",
            "FocusCommsPanel_Buggy": "SRV Comms",
            "QuickCommsPanel_Buggy": "SRV Quick Comms",
            "FocusRadarPanel_Buggy": "SRV Radar",
            "FocusRightPanel_Buggy": "SRV Right Panel",
            "GalaxyMapOpen_Buggy": "SRV Galaxy Map",
            "SystemMapOpen_Buggy": "SRV System Map",
            "OpenCodexGoToDiscovery_Buggy": "SRV Codex",
            "PlayerHUDModeToggle_Buggy": "SRV HUD Mode",
            "HeadLookToggle_Buggy": "SRV Head Look",
            "HumanoidForwardAxis": "Forward",
            "HumanoidForwardButton": "Forward",
            "HumanoidBackwardButton": "Backward",
            "HumanoidStrafeAxis": "Strafe",
            "HumanoidStrafeLeftButton": "Strafe Left",
            "HumanoidStrafeRightButton": "Strafe Right",
            "HumanoidRotateAxis": "Rotate",
            "HumanoidRotateLeftButton": "Turn Left",
            "HumanoidRotateRightButton": "Turn Right",
            "HumanoidPitchAxis": "Look Up/Down",
            "HumanoidPitchUpButton": "Look Up",
            "HumanoidPitchDownButton": "Look Down",
            "HumanoidSprintButton": "Sprint",
            "HumanoidWalkButton": "Walk",
            "HumanoidCrouchButton": "Crouch",
            "HumanoidJumpButton": "Jump",
            "HumanoidPrimaryInteractButton": "Primary Interact",
            "HumanoidSecondaryInteractButton": "Secondary Interact",
            "HumanoidItemWheelButton": "Item Wheel",
            "HumanoidEmoteWheelButton": "Emote Wheel",
            "HumanoidUtilityWheelCycleMode": "Utility Wheel",
            "HumanoidItemWheelButton_XAxis": "Item Wheel X",
            "HumanoidItemWheelButton_YAxis": "Item Wheel Y",
            "HumanoidPrimaryFireButton": "Primary Fire",
            "HumanoidZoomButton": "Zoom",
            "HumanoidThrowGrenadeButton": "Throw Grenade",
            "HumanoidMeleeButton": "Melee",
            "HumanoidReloadButton": "Reload",
            "HumanoidSwitchWeapon": "Switch Weapon",
            "HumanoidSelectPrimaryWeaponButton": "Primary Weapon",
            "HumanoidSelectSecondaryWeaponButton": "Secondary Weapon",
            "HumanoidSelectUtilityWeaponButton": "Utility Weapon",
            "HumanoidSelectNextWeaponButton": "Next Weapon",
            "HumanoidSelectPreviousWeaponButton": "Previous Weapon",
            "HumanoidHideWeaponButton": "Hide Weapon",
            "HumanoidSelectNextGrenadeTypeButton": "Next Grenade",
            "HumanoidSelectPreviousGrenadeTypeButton": "Previous Grenade",
            "HumanoidToggleFlashlightButton": "Flashlight",
            "HumanoidToggleNightVisionButton": "Night Vision",
            "HumanoidToggleShieldsButton": "Shields",
            "HumanoidClearAuthorityLevel": "Clear Authority",
            "HumanoidHealthPack": "Health Pack",
            "HumanoidBattery": "Battery",
            "HumanoidSelectFragGrenade": "Frag Grenade",
            "HumanoidSelectEMPGrenade": "EMP Grenade",
            "HumanoidSelectShieldGrenade": "Shield Grenade",
            "HumanoidSwitchToRechargeTool": "Recharge Tool",
            "HumanoidSwitchToCompAnalyser": "Composition Analyzer",
            "HumanoidSwitchToSuitTool": "Suit Tool",
            "HumanoidToggleToolModeButton": "Tool Mode",
            "HumanoidPing": "Ping",
            "HumanoidOpenAccessPanelButton": "Access Panel",
            "HumanoidConflictContextualUIButton": "Contextual UI",
            "HumanoidEmoteSlot1": "Emote 1",
            "HumanoidEmoteSlot2": "Emote 2",
            "HumanoidEmoteSlot3": "Emote 3",
            "HumanoidEmoteSlot4": "Emote 4",
            "HumanoidEmoteSlot5": "Emote 5",
            "HumanoidEmoteSlot6": "Emote 6",
            "HumanoidEmoteSlot7": "Emote 7",
            "HumanoidEmoteSlot8": "Emote 8",
            "TargetWingman0" : "Target Wingman 1",
            "TargetWingman1" : "Target Wingman 2",
            "TargetWingman2" : "Target Wingman 3",
            "SelectTargetsTarget" : "Target's Target",
            "ShipSpotLightToggle" : "Ship Lights",
        }

        # Check if we have a custom friendly name for this binding
        if binding_name in FRIENDLY_NAMES:
            return FRIENDLY_NAMES[binding_name]

        # Otherwise, apply automatic formatting
        import re
        # Convert camelCase/PascalCase to space separated
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', binding_name)
        # Handle cases like "PrimaryFire" -> "Primary Fire"
        name = re.sub(r'([a-zA-Z])([A-Z][a-z])', r'\1 \2', name)
        # Remove "Button" suffix as it's redundant in context
        name = re.sub(r'\s+Button$', '', name)
        return name.strip().title()

    def parse(self) -> ProfileCollection:
        """Parse the Elite Dangerous bindings file and return a ProfileCollection."""
        parsed_xml = self.parse_file_data(self.data)
        root = parsed_xml.documentElement

        profile_collection = ProfileCollection()

        # Define the different control schemes/profiles in Elite Dangerous
        control_schemes = {
            "Flight": [],  # Main flight controls (no suffix)
            "Landing": [],  # Landing controls (_Landing suffix)
            "SRV": [],  # SRV/Buggy controls (_Buggy suffix)
            "On Foot": [],  # On foot controls (_Humanoid suffix)
            "General": []  # General controls that apply to multiple schemes
        }

        # Find all binding elements and categorize them by control scheme
        for child in root.childNodes:
            if child.nodeType == child.ELEMENT_NODE and child.tagName not in ["KeyboardLayout"]:
                binding_name = child.tagName

                # Determine which control scheme this binding belongs to
                if binding_name.endswith("_Landing"):
                    scheme = "Flight"
                    clean_name = binding_name[:-8]  # Remove "_Landing"
                elif binding_name.endswith("_Buggy"):
                    scheme = "SRV"
                    clean_name = binding_name[:-6]  # Remove "_Buggy"
                elif binding_name.endswith("_Humanoid"):
                    scheme = "On Foot"
                    clean_name = binding_name[:-9]  # Remove "_Humanoid"
                elif binding_name.startswith("Humanoid"):
                    scheme = "On Foot"
                    clean_name = binding_name[8:]  # Remove "Humanoid" prefix
                elif binding_name.startswith("Buggy"):
                    scheme = "SRV"
                    clean_name = binding_name[6:]  # Remove "Buggy" prefix
                elif "Buggy" in binding_name:
                    scheme = "SRV"
                    clean_name = binding_name
                else:
                    # Categorize controls that don't have specific suffixes
                    # General controls are UI, camera, and system-wide controls available across all game modes
                    if any(binding_name.startswith(prefix) for prefix in [
                        # UI Controls
                        "UI", "Focus", "GalaxyMap", "SystemMap", "Codex", "FriendsMenu",
                        "CycleNextPanel", "CyclePreviousPanel", "CycleNextPage", "CyclePreviousPage",
                        "QuickCommsPanel", "PlayerHUDModeToggle", "ShowPGScoreSummaryInput",

                        # Camera Controls
                        "CamPitch", "CamYaw", "CamTranslate", "CamZoom", "CamTranslateZHold",
                        "HeadLook", "MouseHeadlook", "MotionHeadlook",
                        "PitchCamera", "YawCamera", "RollCamera",

                        # System-wide Controls
                        "Pause", "HMDReset", "MicrophoneMute", "PhotoCamera", "VanityCamera",
                        "FreeCam", "MoveFreeCam", "ToggleRotationLock", "FixCameraRelativeToggle",
                        "FixCameraWorldToggle", "QuitCamera", "ToggleAdvanceMode", "FreeCamZoom",
                        "FStop", "CommanderCreator", "GalnetAudio", "GalaxyMapHome",

                        # Multi-crew and Orders
                        "MultiCrew", "Order",

                        # Audio and Communication
                        "OpenCodexGoToDiscovery",

                        # System-wide flight functions (available across modes)
                        "UseBoostJuice", "Supercruise", "Hyperspace", "ToggleDriveAssist"
                    ]):
                        scheme = "General"
                        clean_name = binding_name
                    else:
                        # Everything else goes to Flight (main flight controls)
                        scheme = "Flight"
                        clean_name = binding_name

                # Get the human readable name
                human_name = self.get_human_readable_name(clean_name)

                # Process Primary binding
                primary_elem = None
                secondary_elem = None
                binding_elem = None

                for subchild in child.childNodes:
                    if subchild.nodeType == subchild.ELEMENT_NODE:
                        if subchild.tagName == "Primary":
                            primary_elem = subchild
                        elif subchild.tagName == "Secondary":
                            secondary_elem = subchild
                        elif subchild.tagName == "Binding":
                            binding_elem = subchild

                # Process bindings
                bindings_to_process = []
                if primary_elem:
                    bindings_to_process.append(("Primary", primary_elem))
                if secondary_elem:
                    bindings_to_process.append(("Secondary", secondary_elem))
                if binding_elem:
                    bindings_to_process.append(("Binding", binding_elem))

                for binding_type, elem in bindings_to_process:
                    binding_info = self.parse_binding_element(elem)
                    if binding_info:
                        device_name, key = binding_info
                        resolved_input = self.resolve_input(device_name, key)

                        if resolved_input:
                            device_guid, input_control = resolved_input

                            # Store binding info for this scheme
                            control_schemes[scheme].append({
                                'device_guid': device_guid,
                                'device_name': device_name,
                                'input_control': input_control,
                                'human_name': human_name
                            })

        # Create profiles for each control scheme that has bindings
        for scheme_name, bindings in control_schemes.items():
            if bindings:  # Only create profile if it has bindings
                profile_obj = profile_collection.create_profile(scheme_name)

                for binding in bindings:
                    # Add device to profile (add_device handles duplicates internally)
                    device_obj = profile_obj.add_device(binding['device_guid'], binding['device_name'])

                    if device_obj and binding['input_control']:
                        device_obj.create_input(binding['input_control'], binding['human_name'])

        return profile_collection


if __name__ == "__main__":
    pass