#!/usr/bin/env python3
"""
Comprehensive test of French descriptions on different devices
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from joystick_diagrams.plugins.il2_sturmovik_plugin.il2_parser import IL2Parser

def test_comprehensive_french_descriptions():
    """Complete test of French descriptions on all devices"""
    
    print("=== Complete French Descriptions Test ===")
    
    # Use test directory
    test_dir = Path(__file__).parent
    
    # Initialize and process
    parser = IL2Parser(test_dir)
    profile_collection = parser.process_profiles()
    
    print(f"✅ Processed profile with {len(profile_collection.profiles)} profiles")
    
    french_count = 0
    technical_count = 0
    
    for profile_name, profile in profile_collection.profiles.items():
        for device_guid, device in profile.devices.items():
            print(f"\n🎮 Device: {device.name}")
            
            device_french = 0
            device_technical = 0
            
            for input_type, inputs in device.inputs.items():
                for input_obj in inputs.values():
                    command = input_obj.command
                    control = input_obj.input_control
                    
                    # Check if command contains French description (has special characters or known French words)
                    is_french = any(char in command for char in "àâäéèêëìîïòôöùûüç") or \
                               any(word in command.lower() for word in ["de", "du", "des", "la", "le", "les", "avec", "toutes", "armes", "trim", "profondeur", "roulis"])
                    
                    if is_french:
                        device_french += 1
                        french_count += 1
                        print(f"   🇫🇷 {command} → {control.identifier}")
                    else:
                        device_technical += 1
                        technical_count += 1
                        # Only show first few technical names to not clutter output
                        if device_technical <= 3:
                            print(f"   🔧 {command} → {control.identifier}")
            
            if device_technical > 3:
                print(f"   ... and {device_technical - 3} more technical bindings")
            
            print(f"   📊 Device summary: {device_french} French, {device_technical} technical")
    
    print(f"\n📊 Overall Summary:")
    print(f"   🇫🇷 French descriptions: {french_count}")
    print(f"   🔧 Technical names: {technical_count}")
    print(f"   📈 French coverage: {french_count/(french_count + technical_count)*100:.1f}%")
    
    if french_count > 0:
        print(f"\n🎉 SUCCESS: French descriptions are being displayed!")
    else:
        print(f"\n❌ ISSUE: No French descriptions found")

if __name__ == "__main__":
    test_comprehensive_french_descriptions()