#!/usr/bin/env python3
"""Very simple test to diagnose button creation problem"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from joystick_diagrams.plugins.il2_sturmovik_plugin.il2_parser import IL2Parser

def test_button_creation():
    """Simple button creation test"""
    print("=== Test button creation joy3_b34 ===")
    
    test_dir = Path(__file__).parent
    parser = IL2Parser(test_dir)
    
    # Direct parsing test
    result = parser._parse_il2_device_reference('joy3_b34')
    print(f"Parsing result: {result}")
    
    if result and result.get('type') == 'button':
        # Control object creation test
        try:
            control = parser._create_control_object(result)
            if control:
                print(f"✅ Control object created: {type(control)}")
                print(f"   Identifier: {getattr(control, 'identifier', 'NO IDENTIFIER')}")
                print(f"   Button ID: {getattr(control, 'button_id', 'NO BUTTON_ID')}")
            else:
                print("❌ Control object is None")
        except Exception as e:
            print(f"❌ Control creation error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== Complete binding test ===")
    # Complete binding test for escape (joy3_b34)
    try:
        profile_collection = parser.process_profiles()
        
        # Find joy3_b34 binding
        joy3_bindings = [b for b in parser.bindings if b['device_ref'] == 'joy3_b34']
        for binding in joy3_bindings:
            print(f"Binding found: {binding}")
            
            # Test control creation
            control = parser._create_control_object(binding)
            if control:
                print(f"✅ Control created for binding: {type(control)}")
            else:
                print(f"❌ Failed to create control for binding")
                
    except Exception as e:
        print(f"❌ Complete test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_button_creation()