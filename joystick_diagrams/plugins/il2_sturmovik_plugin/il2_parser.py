"""IL-2 Sturmovik globals.actions Parser for use with Joystick Diagrams"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.hat import Hat, HatDirection
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.input.device import INPUT_TYPE_IDENTIFIERS

_logger = logging.getLogger(__name__)

# IL-2 control type mappings
AXIS_MAPPINGS = {
    "X": AxisDirection.X,
    "Y": AxisDirection.Y,
    "Z": AxisDirection.Z,
    "RX": AxisDirection.RX,
    "RY": AxisDirection.RY,
    "RZ": AxisDirection.RZ,
    # U and V axes are mapped to AxisSlider instead since they're not standard DirectX axes
}

HAT_DIRECTION_MAPPINGS = {
    "U": HatDirection.U,
    "D": HatDirection.D,
    "L": HatDirection.L,
    "R": HatDirection.R,
    "UL": HatDirection.UL,
    "UR": HatDirection.UR,
    "DL": HatDirection.DL,
    "DR": HatDirection.DR,
}


class IL2Parser:
    """Parser for IL-2 Sturmovik input directory (global.actions + devices.txt)"""

    def __init__(self, input_dir: Path):
        self.input_dir = input_dir
        self.global_actions_file = input_dir / "global.actions"
        self.devices_file = input_dir / "devices.txt"
        self.devices: Dict[str, Dict] = {}
        self.bindings: List[Dict] = []
        self.action_descriptions: Dict[str, str] = {}

    def process_profiles(self) -> ProfileCollection:
        """Main processing method to create ProfileCollection from IL-2 config"""
        _logger.info(f"Starting to process IL-2 profiles from: {self.input_dir}")
        profile_collection = ProfileCollection()

        try:
            # Clear previous data to ensure fresh parsing
            self.devices.clear()
            self.bindings.clear()
            self.action_descriptions.clear()
            _logger.debug("Cleared previous parsing data")
            
            self._parse_devices_file()
            self._parse_global_actions_file()
            _logger.info(f"Files parsed successfully. Found {len(self.devices)} devices and {len(self.bindings)} bindings")
            self._create_profiles(profile_collection)
            _logger.info(f"Profile creation completed. Created {len(profile_collection.profiles)} profiles")
        except Exception as e:
            _logger.error(f"Error processing IL-2 profiles: {e}")
            raise

        return profile_collection

    def _parse_devices_file(self):
        """Parse the devices.txt file to get real device names"""
        try:
            _logger.info(f"Opening devices file: {self.devices_file}")
            
            # Try different encodings for devices.txt
            encodings_to_try = ["utf-8", "windows-1252", "latin-1", "cp1252"]
            content = None
            
            for encoding in encodings_to_try:
                try:
                    with open(self.devices_file, "r", encoding=encoding) as file:
                        content = file.read()
                    _logger.info(f"Devices file read successfully with {encoding} encoding. Content length: {len(content)} characters")
                    break
                except UnicodeDecodeError:
                    _logger.debug(f"Failed to read devices file with {encoding} encoding, trying next...")
                    continue
            
            if content is None:
                raise UnicodeDecodeError("Failed to read devices file with any supported encoding")
            
            self._extract_device_info(content)

        except Exception as e:
            _logger.error(f"Error parsing devices file {self.devices_file}: {e}")
            raise

    def _parse_global_actions_file(self):
        """Parse the global.actions file"""
        try:
            _logger.info(f"Opening global.actions file: {self.global_actions_file}")
            
            # Try different encodings for global.actions
            encodings_to_try = ["utf-8", "windows-1252", "latin-1", "cp1252"]
            content = None
            
            for encoding in encodings_to_try:
                try:
                    with open(self.global_actions_file, "r", encoding=encoding) as file:
                        content = file.read()
                    _logger.info(f"Global.actions file read successfully with {encoding} encoding. Content length: {len(content)} characters")
                    break
                except UnicodeDecodeError:
                    _logger.debug(f"Failed to read global.actions with {encoding} encoding, trying next...")
                    continue
            
            if content is None:
                raise UnicodeDecodeError("Failed to read global.actions file with any supported encoding")
            
            # Fix encoding issues caused by double-encoding (UTF-8 saved as Windows-1252)
            content = self._fix_encoding_issues(content)
            
            self._extract_bindings(content)

        except Exception as e:
            _logger.error(f"Error parsing global.actions file {self.global_actions_file}: {e}")
            raise

    def _fix_encoding_issues(self, content: str) -> str:
        """Fix common encoding issues found in IL-2 Sturmovik files
        
        IL-2 files sometimes contain UTF-8 characters that were saved in Windows-1252 files,
        causing double-encoding issues.
        """
        import re
        
        fixed_content = content
        changes_made = 0
        
        # Convert to bytes and back to properly handle encoding issues
        try:
            # Encode as latin1 to get original bytes, then decode as utf-8
            # This fixes double-encoding where UTF-8 was saved as latin1/windows-1252
            bytes_content = fixed_content.encode('latin1')
            
            # Try to decode problematic sequences as UTF-8
            # Look for the UTF-8 byte sequence for right single quotation mark (')
            # UTF-8: \xe2\x80\x99 appears as â€™ when decoded as latin1
            if b'\xe2\x80\x99' in bytes_content:
                # Replace the UTF-8 apostrophe bytes with simple apostrophe
                bytes_content = bytes_content.replace(b'\xe2\x80\x99', b"'")
                changes_made += 1
                
            # Fix en-dash (UTF-8: \xe2\x80\x93)
            if b'\xe2\x80\x93' in bytes_content:
                bytes_content = bytes_content.replace(b'\xe2\x80\x93', b'-')
                changes_made += 1
                
            # Decode back to string
            if changes_made > 0:
                fixed_content = bytes_content.decode('latin1')
                
        except Exception as e:
            _logger.debug(f"Byte-level encoding fix failed: {e}, trying string replacements")
            
            # Fallback: Simple string replacements for the most common cases 
            # Using character codes to avoid encoding issues in source code
            double_encoded_patterns = [
                ("\u00e2\u20ac\u2122", "'"),  # â€™ -> ' (right single quotation mark)
                ("\u00e2\u20ac\u0153", '"'),  # â€œ -> " (left double quotation mark)  
                ("\u00e2\u20ac\ufffd", '"'),  # â€� -> " (right double quotation mark)
                ("\u00e2\u20ac\u201c", "-"),  # â€" -> - (en dash)
                ("\u00e2\u20ac\u201d", "-"),  # â€" -> - (em dash)
            ]
            
            for bad, good in double_encoded_patterns:
                if bad in fixed_content:
                    old_content = fixed_content
                    fixed_content = fixed_content.replace(bad, good)
                    if fixed_content != old_content:
                        changes_made += 1
        
        # Log if we made changes
        if changes_made > 0:
            _logger.info(f"Fixed {changes_made} encoding issues in global.actions file")
        
        return fixed_content

    def _extract_device_info(self, content: str):
        """Extract device information from devices.txt"""
        # devices.txt format: configId,guid,model|
        # Example: 0,%22b02d6330-3f30-11f0-0000545345440280%22,Throttle%20-%20HOTAS%20Warthog|
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if (
                not stripped_line
                or stripped_line.startswith("//")
                or stripped_line.startswith("configId,")  # Header line
            ):
                continue
                
            if not stripped_line.endswith("|"):
                # Check if this is the last line without trailing |
                if not (line_num == len(lines) and len(stripped_line.split(",")) >= 3):
                    continue
                
            # Remove trailing | if present and split by comma
            if stripped_line.endswith("|"):
                parts = stripped_line[:-1].split(",")
            else:
                parts = stripped_line.split(",")
            
            if len(parts) < 3:
                continue
                
            try:
                config_id = parts[0].strip()
                guid_encoded = parts[1].strip()
                model_encoded = parts[2].strip()
                
                # Decode URL-encoded strings
                import urllib.parse
                guid = urllib.parse.unquote(guid_encoded)
                model = urllib.parse.unquote(model_encoded)
                
                # Remove quotes from GUID
                if guid.startswith('"') and guid.endswith('"'):
                    guid = guid[1:-1]
                
                # Generate deterministic UUID for this device based on config_id
                import uuid
                namespace = uuid.UUID('12345678-1234-5678-9abc-123456789abc')
                device_uuid = uuid.uuid5(namespace, f"il2_joy_{config_id}")
                
                self.devices[config_id] = {
                    "name": model,
                    "id": config_id,
                    "guid": str(device_uuid),
                    "original_guid": guid
                }
                _logger.debug(f"Found device: {model} (joy{config_id}) with GUID: {device_uuid}")
                
            except Exception as e:
                _logger.warning(f"Failed to parse device line {line_num}: {stripped_line} - {e}")
                continue
                
        _logger.info(f"Extracted {len(self.devices)} devices from devices.txt")

    def _extract_bindings(self, content: str):
        """Extract control bindings from the file"""
        # IL-2 format: action_name, device_reference, invert|
        # Split content into lines for easier parsing
        lines = content.split("\n")
        
        # First pass: build action descriptions mapping
        self._build_action_descriptions(lines)
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if (
                not stripped_line
                or stripped_line.startswith("//")
                or stripped_line.startswith("#")
                or stripped_line.startswith("&actions=")
            ):
                continue

            bindings = self._parse_binding_line(stripped_line, line_num)
            if bindings:
                # bindings peut être une liste ou un seul binding
                if isinstance(bindings, list):
                    self.bindings.extend(bindings)
                else:
                    self.bindings.append(bindings)
                
        _logger.info(f"Extracted {len(self.bindings)} bindings from IL-2 config")

    def _build_action_descriptions(self, lines: List[str]):
        """Build a mapping from action names to their descriptions"""
        self.action_descriptions = {}
        
        for line in lines:
            stripped_line = line.strip()
            if (
                not stripped_line
                or stripped_line.startswith("//")
                or stripped_line.startswith("#")
                or stripped_line.startswith("&actions=")
            ):
                continue

            # Check if this line has a comment with description
            if '|' not in line:
                continue
                
            binding_parts = line.split('|', 1)
            if len(binding_parts) > 1 and binding_parts[1].strip():
                comment_part = binding_parts[1].strip()
                # Look for description after //
                if comment_part.startswith('//'):
                    description = comment_part[2:].strip()
                    if description:
                        # Extract action name from the binding part
                        binding_part = binding_parts[0]
                        parts = binding_part.split(",")
                        if len(parts) >= 1:
                            action_name = parts[0].strip()
                            # Store description for this action
                            self.action_descriptions[action_name] = description
                            _logger.debug(f"Found description for '{action_name}': '{description}'")

    def _parse_binding_line(self, line: str, line_num: int) -> Union[Dict, List[Dict], None]:
        """Parse a single binding line in IL-2 format
        
        Returns:
            Dict: Single binding for simple device references
            List[Dict]: Multiple bindings for device references with slash separator
            None: If line cannot be parsed
        """
        # IL-2 format: action_name, device_reference, invert| [// comment]
        # Example: rpc_pitch, joy9_axis_y, 0| // Some comment
        # Example with multiple refs: rpc_pitch_trim, joy9_pov0_0/joy9_pov0_180, 0|
        
        # First, split by | to separate the binding from any comment
        if '|' not in line:
            return None
            
        binding_parts = line.split('|', 1)  # Split only on first |
        binding_part = binding_parts[0] + '|'  # Keep only the part before |, add | back
        
        if not binding_part.endswith("|"):
            return None
            
        # Remove the trailing | and split by comma
        parts = binding_part[:-1].split(",")
        if len(parts) < 2:
            return None
            
        action_name = parts[0].strip()
        device_ref = parts[1].strip()
        invert = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else 0
        
        # Use description from our pre-built mapping
        description = self.action_descriptions.get(action_name)
        
        # Skip keyboard and mouse bindings, focus on joystick
        if not device_ref.startswith("joy"):
            return None
        
        # Check if device_ref contains multiple references separated by slash
        if '/' in device_ref:
            # Multiple device references: joy9_pov0_0/joy9_pov0_180
            device_refs = [ref.strip() for ref in device_ref.split('/')]
            bindings = []
            
            for individual_ref in device_refs:
                control_info = self._parse_il2_device_reference(individual_ref)
                if control_info:
                    bindings.append({
                        "action": action_name,
                        "device_ref": individual_ref,
                        "invert": invert,
                        "line_num": line_num,
                        "description": description,  # Add description from comment
                        **control_info,
                    })
            
            return bindings if bindings else None
        else:
            # Single device reference
            control_info = self._parse_il2_device_reference(device_ref)
            if not control_info:
                return None

            return {
                "action": action_name,
                "device_ref": device_ref,
                "invert": invert,
                "line_num": line_num,
                "description": description,  # Add description from comment
                **control_info,
            }

    def _parse_il2_device_reference(self, device_ref: str) -> Optional[Dict]:
        """Parse IL-2 device reference like joy9_axis_y, joy3_b41, joy0_pov0_270, joy10_b1"""
        
        # Pattern for button: joy3_b41, joy10_b1
        button_match = re.match(r'joy(\d+)_b(\d+)', device_ref)
        if button_match:
            joy_number = int(button_match.group(1))
            il2_button_id = int(button_match.group(2))
            
            # Convert joy number to device ID
            # Direct mapping: joy0 -> device 0, joy1 -> device 1, joy10 -> device 10, etc.
            device_id = str(joy_number)
                
            # Convert from IL-2's internal numbering to physical joystick numbering
            # IL-2 uses 0-based indexing internally, but physical buttons are 1-based
            # So joy3_b41 in file = physical button 42
            button_id = il2_button_id + 1
            return {
                "type": "button", 
                "device_id": device_id,
                "button_id": button_id
            }
        
        # Pattern for axis: joy9_axis_y, joy8_axis_w, joy10_axis_x
        axis_match = re.match(r'joy(\d+)_axis_([xyzwqsturp])', device_ref)
        if axis_match:
            joy_number = int(axis_match.group(1))
            il2_axis_letter = axis_match.group(2).lower()
            
            # Convert joy number to device ID (direct mapping)
            device_id = str(joy_number)
            
            # Map IL-2 axis letters to DirectInput axis names
            axis_mapping = {
                'x': 'X',          # IL-2 axis_x is AXIS_X
                'y': 'Y',          # IL-2 axis_y is AXIS_Y  
                'z': 'Z',          # IL-2 axis_z is AXIS_Z
                'w': 'RX',          # IL-2 axis_w is AXIS_RX
                's': 'RY',          # IL-2 axis_s is AXIS_RY
                'q': 'SLIDER_2',    # IL-2 axis_q is AXIS_SLIDER_2
                'p': 'SLIDER_1',    # IL-2 axis_p is AXIS_SLIDER_1
                't': 'RZ',          # Assuming axis_t is rudder (RZ)
                'u': 'U',           # Additional axis
                'r': 'V'            # Additional axis
            }
            
            axis_id = axis_mapping.get(il2_axis_letter, il2_axis_letter.upper())
                
            return {
                "type": "axis",
                "device_id": device_id, 
                "axis_id": axis_id
            }
            
        # Pattern for POV/HAT: joy0_pov0_270, joy9_pov0_0, joy10_pov0_180
        pov_match = re.match(r'joy(\d+)_pov(\d+)_(\d+)', device_ref)
        if pov_match:
            joy_number = int(pov_match.group(1))
            pov_id = int(pov_match.group(2))
            direction = int(pov_match.group(3))
            
            # Convert joy number to device ID (direct mapping)
            device_id = str(joy_number)
            
            # Map IL-2 POV directions to DirectInput HAT names
            # POV0 = POV_1, POV1 = POV_2, etc.
            pov_name = f"POV_{pov_id + 1}"
            
            # Map direction angles to directional names
            direction_mapping = {
                0: "U",      # Up (North)
                45: "UR",    # Up-Right (North-East)
                90: "R",     # Right (East)
                135: "DR",   # Down-Right (South-East)
                180: "D",    # Down (South)
                225: "DL",   # Down-Left (South-West)
                270: "L",    # Left (West)
                315: "UL",   # Up-Left (North-West)
            }
            
            direction_name = direction_mapping.get(direction, str(direction))
            hat_direction = f"{pov_name}_{direction_name}"
                
            return {
                "type": "hat",
                "device_id": device_id,
                "hat_id": hat_direction,
                "direction": direction
            }
            
        return None



    def _create_profiles(self, profile_collection: ProfileCollection):
        """Create profiles and devices from parsed data"""
        # Create a single profile for IL-2
        profile = profile_collection.create_profile("IL-2 Sturmovik")

        # Use pre-built description mapping
        action_descriptions = self.action_descriptions

        # Group bindings by device ID
        device_bindings: Dict[str, List[Dict]] = {}

        for binding in self.bindings:
            device_id = binding["device_id"]
            if device_id not in device_bindings:
                device_bindings[device_id] = []
            device_bindings[device_id].append(binding)

        # Create devices and add bindings
        for device_id, bindings in device_bindings.items():
            # Get device info from devices.txt mapping or create default
            device_info = self.devices.get(device_id)
            if device_info:
                device_name = device_info["name"]
                device_guid = device_info["guid"]
                _logger.debug(f"Found device mapping for joy{device_id}: {device_name}")
            else:
                # Fallback for devices not in devices.txt
                device_name = f"IL-2 Joystick {device_id}"
                _logger.warning(f"No device mapping found for joy{device_id} in devices.txt. Available device IDs: {list(self.devices.keys())}")
                # Generate consistent UUID for unmapped devices
                import uuid
                namespace = uuid.UUID('12345678-1234-5678-9abc-123456789abc')
                device_guid = str(uuid.uuid5(namespace, f"il2_joy_{device_id}"))
            
            device = profile.add_device(device_guid, device_name)

            for binding in bindings:
                control = self._create_control_object(binding)
                if control:
                    # Use description if available, otherwise use action name
                    action_name = binding["action"]
                    display_name = action_descriptions.get(action_name, action_name)
                    
                    # Check if we have an existing input for the same control
                    type_key = device.resolve_type(control)
                    identifier = getattr(control, INPUT_TYPE_IDENTIFIERS[type_key])
                    existing_input = device.get_input(type_key, identifier)
                    
                    if existing_input:
                        # Combine commands instead of overwriting
                        if existing_input.command and existing_input.command != display_name:
                            existing_input.command = f"{existing_input.command} | {display_name}"
                            _logger.debug(f"Combined commands for {control.identifier}: {existing_input.command}")
                        elif not existing_input.command:
                            existing_input.command = display_name
                            _logger.debug(f"Set command for existing input {control.identifier}: {display_name}")
                    else:
                        # Create new input
                        device.create_input(control, display_name)
                        _logger.debug(f"Created input for {display_name} → {control.identifier}")
                else:
                    _logger.warning(f"Failed to create control object for binding: {binding}")

    def _create_control_object(
        self, binding: Dict
    ) -> Optional[Union[Button, Axis, Hat, AxisSlider]]:
        """Create appropriate control object from binding data"""
        control_type = binding["type"]

        try:
            if control_type == "button":
                return Button(binding["button_id"])

            elif control_type == "axis":
                axis_id = binding["axis_id"]
                if axis_id in AXIS_MAPPINGS:
                    return Axis(AXIS_MAPPINGS[axis_id])
                elif axis_id in ["U", "V", "Q", "S", "W", "T", "R"]:
                    # Map non-standard axes to sliders
                    # IL-2 uses various axis letters
                    slider_mapping = {"U": 1, "V": 2, "Q": 3, "S": 4, "W": 5, "T": 6, "R": 7}
                    slider_id = slider_mapping.get(axis_id, 1)
                    return AxisSlider(slider_id)
                elif axis_id.startswith("SLIDER_"):
                    # Handle mapped slider axes like "SLIDER_1", "SLIDER_2"
                    try:
                        slider_id = int(axis_id.split("_")[1])
                        return AxisSlider(slider_id)
                    except (IndexError, ValueError) as e:
                        _logger.warning(f"Invalid slider axis_id format: {axis_id}, error: {e}")
                        return None

            elif control_type == "hat":
                hat_id_str = binding["hat_id"]  # e.g., "POV_1_U"
                direction_degrees = binding["direction"]
                
                # Extract numeric HAT ID from string like "POV_1_U" -> 1
                import re
                hat_match = re.match(r"POV_(\d+)_", hat_id_str)
                if hat_match:
                    hat_id_numeric = int(hat_match.group(1))
                else:
                    _logger.warning(f"Could not extract HAT ID from {hat_id_str}, using 1")
                    hat_id_numeric = 1
                
                # Convert degrees to direction
                direction_map = {0: HatDirection.U, 45: HatDirection.UR, 90: HatDirection.R, 
                               135: HatDirection.DR, 180: HatDirection.D, 225: HatDirection.DL,
                               270: HatDirection.L, 315: HatDirection.UL}
                direction = direction_map.get(direction_degrees, HatDirection.U)
                return Hat(hat_id_numeric, direction)

        except Exception as e:
            _logger.error(f"Error creating control object for binding {binding}: {e}")

        return None

    def export_mapping_to_file(self, output_file_path: Path, profile_collection: ProfileCollection = None) -> bool:
        """Export IL-2 mappings to a CSV file
        
        Args:
            output_file_path: Path where to save the export.csv file
            profile_collection: Optional ProfileCollection to export (if None, will process fresh)
            
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            import csv
            
            # Work directly from bindings instead of processed profiles
            # This ensures we have all the original IL-2 data
            if not self.bindings:
                # Process to populate bindings
                self._parse_devices_file()
                self._parse_global_actions_file()
            
            export_data = []
            
            # Group bindings by device for organized export
            device_bindings = {}
            for binding in self.bindings:
                device_id = binding['device_id']
                if device_id not in device_bindings:
                    device_bindings[device_id] = []
                device_bindings[device_id].append(binding)
            
            # Export each device's bindings
            for device_id, bindings in device_bindings.items():
                # Get device info
                device_info = self.devices.get(device_id, {})
                device_name = device_info.get('name', f'IL-2 Joystick {device_id}')
                
                for binding in bindings:
                    technical_name = binding.get('action', 'Unknown')
                    description = binding.get('description', technical_name)
                    il2_reference = binding.get('device_ref', 'Unknown')
                    
                    # Generate real button/control identifier
                    real_control = self._generate_real_control_identifier(binding)
                    
                    export_data.append({
                        'device_name': device_name,
                        'technical_name': technical_name,
                        'description': description,
                        'il2_button': il2_reference,
                        'real_button': real_control
                    })
            
            # Write to CSV file
            with open(output_file_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['Device', 'Technical_Name', 'Description', 'IL2_Control', 'Real_Control']
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                
                # Write header
                writer.writeheader()
                
                # Write data (sorted by device name and real control)
                for item in sorted(export_data, key=lambda x: (x['device_name'], x['real_button'])):
                    writer.writerow({
                        'Device': item['device_name'],
                        'Technical_Name': item['technical_name'], 
                        'Description': item['description'],
                        'IL2_Control': item['il2_button'],
                        'Real_Control': item['real_button']
                    })
            
            _logger.info(f"Successfully exported {len(export_data)} mappings to CSV file {output_file_path}")
            return True
            
        except Exception as e:
            _logger.error(f"Failed to export mappings to CSV file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_real_control_identifier(self, binding: dict) -> str:
        """Generate the real control identifier (like BUTTON_35, AXIS_RX, etc.)"""
        try:
            control_type = binding.get('type', 'unknown')
            
            if control_type == 'button':
                button_id = binding.get('button_id', 0)
                return f"BUTTON_{button_id}"
                
            elif control_type == 'axis':
                axis_id = binding.get('axis_id', 'UNKNOWN')
                return f"AXIS_{axis_id}"
                
            elif control_type == 'hat':
                hat_id = binding.get('hat_id', 'UNKNOWN')
                return f"HAT_{hat_id}"
                
            else:
                return f"UNKNOWN_{control_type}"
                
        except Exception as e:
            return "ERROR"
    
    def _find_il2_reference_for_input(self, input_item, device_name: str) -> str:
        """Find the original IL-2 reference (like joy3_b34) for an input"""
        identifier = getattr(input_item, 'identifier', '')
        
        # Try to find matching binding
        for binding in self.bindings:
            if self._binding_matches_input(binding, input_item):
                return binding.get('device_ref', 'Unknown')
        
        return 'Unknown'
    
    def _binding_matches_input(self, binding: dict, input_item) -> bool:
        """Check if a binding matches an input item"""
        try:
            input_type = type(input_item).__name__.lower()
            binding_type = binding.get('type', '')
            
            if input_type == 'button' and binding_type == 'button':
                input_id = getattr(input_item, 'identifier', '')
                if 'BUTTON_' in input_id:
                    button_num = int(input_id.replace('BUTTON_', ''))
                    return binding.get('button_id') == button_num
                    
            elif input_type == 'axis' and binding_type == 'axis':
                input_axis = getattr(input_item, 'axis_direction', None)
                if input_axis:
                    axis_name = input_axis.name
                    return binding.get('axis_id') == axis_name
                    
            elif input_type == 'hat' and binding_type == 'hat':
                input_id = getattr(input_item, 'identifier', '')
                return binding.get('hat_id', '').replace('_', '') in input_id.replace('_', '')
                
        except Exception:
            pass
            
        return False
    
    def _get_device_id_from_guid(self, device_guid: str, device_name: str) -> str:
        """Get the original device ID from GUID or name"""
        # Try to find the device ID from our devices mapping
        for device_id, device_info in self.devices.items():
            if device_info.get('guid') == device_guid or device_info.get('name') == device_name:
                return device_id
        
        return 'Unknown'


if __name__ == "__main__":
    # Test the parser
    pass
