'''Joystick Gremlin (Version ~13) XML Parser for use with Joystick Diagrams'''
from xml.dom import minidom
import functions.helper as helper
import adaptors.joystick_diagram_interface as jdi

hats = {
    'up': "U",
    'down': "D",
    'left': "L",
    'right': "R"
}

joystick_dictionary = {}
button_array = {}

data = '''
<ActionMaps version="1" optionsVersion="2" rebindVersion="2" profileName="VKB">
 <CustomisationUIHeader label="VKB" description="" image="">
  <devices>
   <keyboard instance="1"/>
   <mouse instance="1"/>
   <joystick instance="1"/>
   <joystick instance="2"/>
  </devices>
  <categories>
   <category label="@ui_CCSpaceFlight"/>
   <category label="@ui_CGLightControllerDesc"/>
   <category label="@ui_CCFPS"/>
   <category label="@ui_CCVehicle"/>
   <category label="@ui_CGUIGeneral"/>
   <category label="@ui_CGOpticalTracking"/>
   <category label="@ui_CGInteraction"/>
  </categories>
 </CustomisationUIHeader>
 <deviceoptions name="T.16000M {B10A044F-0000-0000-0000-504944564944}">
  <option input="x" deadzone="0.098999992"/>
  <option input="y" deadzone="0.098999992"/>
 </deviceoptions>
 <options type="keyboard" instance="1" Product="Keyboard {6F1D2B61-D5A0-11CF-BFC7-444553540000}"/>
 <options type="joystick" instance="1" Product="T.16000M {B10A044F-0000-0000-0000-504944564944}">
  <flight_move exponent="1.5"/>
  <flight_move_strafe_vertical exponent="3"/>
  <flight_move_strafe_lateral exponent="3"/>
  <flight_move_strafe_longitudinal invert="1" exponent="3"/>
  <flight_move_strafe_forward exponent="1"/>
  <flight_move_strafe_backward exponent="1"/>
  <flight_move_speed_range invert="1" exponent="1"/>
  <flight_move_accel_range invert="1" exponent="1"/>
  <flight_view exponent="1.5"/>
  <turret exponent="1.5"/>
  <turret_limiter_relative invert="1"/>
  <turret_limiter_absolute invert="1"/>
 </options>
 <options type="joystick" instance="2" Product=" VKB-Sim Gladiator NXT R   {0200231D-0000-0000-0000-504944564944}">
  <flight_move exponent="1.5"/>
  <flight_move_strafe_vertical exponent="3"/>
  <flight_move_strafe_lateral exponent="3"/>
  <flight_move_strafe_longitudinal invert="1" exponent="3"/>
  <flight_move_strafe_forward exponent="1"/>
  <flight_move_strafe_backward exponent="1"/>
  <flight_move_speed_range invert="1" exponent="1"/>
  <flight_move_accel_range invert="1" exponent="1"/>
  <flight_view exponent="1.5"/>
  <turret exponent="1.5"/>
  <turret_limiter_relative invert="1"/>
  <turret_limiter_absolute invert="1"/>
 </options>
 <modifiers />
 <actionmap name="spaceship_general">
  <action name="v_flightready">
   <rebind input="js1_rctrl+hat1_down"/>
  </action>
 </actionmap>
 <actionmap name="spaceship_view">
  <action name="v_view_dynamic_zoom_abs">
   <rebind input="js2_z"/>
  </action>
  <action name="v_view_dynamic_zoom_rel_in">
   <rebind input="js2_ "/>
  </action>
  <action name="v_view_pitch_down">
   <rebind input="js2_hat1_down"/>
  </action>
  <action name="v_view_pitch_up">
   <rebind input="js2_hat1_up"/>
  </action>
  <action name="v_view_yaw_left">
   <rebind input="js2_hat1_left"/>
  </action>
  <action name="v_view_yaw_right">
   <rebind input="js2_hat1_right"/>
  </action>

 </actionmap>
 <actionmap name="spaceship_movement">
  <action name="v_accel_range_abs">
   <rebind input="js2_ "/>
  </action>
  <action name="v_accel_range_rel">
   <rebind input="js2_slider1"/>
  </action>
  <action name="v_afterburner">
   <rebind input="js1_button2"/>
  </action>
  <action name="v_autoland">
   <rebind input="js1_rctrl+button3"/>
  </action>
  <action name="v_brake">
   <rebind input="js1_button3"/>
  </action>
  <action name="v_ifcs_toggle_cruise_control">
   <rebind input="js1_button4"/>
  </action>
  <action name="v_ifcs_toggle_esp">
   <rebind input="kb1_lalt+o"/>
   <rebind input="js2_ "/>
  </action>
  <action name="v_ifcs_toggle_gforce_safety">
   <rebind input="kb1_lalt+i"/>
  </action>
  <action name="v_ifcs_toggle_vector_decoupling">
   <rebind input="js1_rctrl+hat1_left"/>
  </action>
  <action name="v_pitch">
   <rebind input="js2_y"/>
  </action>
  <action name="v_roll">
   <rebind input="js2_rotz"/>
  </action>
  <action name="v_speed_range_down">
   <rebind input="js1_hat1_down"/>
  </action>
  <action name="v_speed_range_up">
   <rebind input="js1_hat1_up"/>
  </action>
  <action name="v_strafe_back">
   <rebind input="js1_ "/>
  </action>
  <action name="v_strafe_down">
   <rebind input="js1_ "/>
  </action>
  <action name="v_strafe_forward">
   <rebind input="js1_ "/>
  </action>
  <action name="v_strafe_lateral">
   <rebind input="js1_x"/>
  </action>
  <action name="v_strafe_left">
   <rebind input="js1_ "/>
  </action>
  <action name="v_strafe_longitudinal">
   <rebind input="js1_y"/>
  </action>
  <action name="v_strafe_right">
   <rebind input="js1_ "/>
  </action>
  <action name="v_strafe_up">
   <rebind input="js1_ "/>
  </action>
  <action name="v_strafe_vertical">
   <rebind input="js1_rotz"/>
  </action>
  <action name="v_toggle_landing_system">
   <rebind input="js2_button17"/>
  </action>
  <action name="v_toggle_qdrive_engagement">
   <rebind input="js2_button5"/>
  </action>
  <action name="v_toggle_qdrive_spooling">
   <rebind input="js2_button5"/>
  </action>
  <action name="v_toggle_vtol">
   <rebind input="js2_button29"/>
  </action>
  <action name="v_toggle_yaw_roll_swap">
   <rebind input="js2_ "/>
  </action>
  <action name="v_yaw">
   <rebind input="js2_x"/>
  </action>
 </actionmap>

</ActionMaps>

'''

def convert_hat(hat):
    value = hats[hat]
    return value

def parse_bind(bind):

    segments = bind.split("_")

    bind_device = segments[0]
    device_type = bind_device[0]
    device_id = bind[2]
    device_object = get_device(bind_device)

    # Lookup Device

    if device_type == 'j': 
        print("I'm a joystick")
    else:
        print("I'm a keyboard")

    print(bind,device_type,device_id)

    # Handle Button28
    # Handle HAT1_UP
    # Disregard Modifiers
    print(segments)

    if segments[1] == ' ':
        print("Blank")
        c_map = None

        return (device_object,c_map)

    elif segments[1][0:6] == 'button':
        print("Button")
        
        button_id = segments[1][6:]
        print(button_id)
        c_map = 'BUTTON_{id}'.format(id=button_id)

        return (device_object,c_map)

    elif segments[1][0:3] == 'hat':
        print("Hat Switch")

        pov_id = segments[1][3:]

        print(pov_id)

        pov_dir = convert_hat(segments[2])
        print(pov_dir)

        c_map = 'POV_{id}_{dir}'.format(id=pov_id,dir=pov_dir)

        return (device_object,c_map)

def add_device(option):
    ''' Accepts parsed OPTION from Starship Citizen XML'''
    devices.update({
        device_id(option.getAttribute('type'),option.getAttribute('instance')) : get_device_information(option)
    })

def get_device_information(option):
    ''' Accepts parsed OPTION from Starship Citizen XML'''

    name = (option.getAttribute('Product')[0:(len(option.getAttribute('Product'))-38)]).strip()
    guid = option.getAttribute('Product')[-37:-2] #GUID Fixed
    return {
        'name': name,
        'guid' : guid
        }

def process_name(name):

    name = name.split("_")

    if len(name) == 1:
        return name[0].capitalize()
    else:
        return (" ".join(name)).capitalize()

def device_id(type, instance):
    if type == 'keyboard':
        t = "kb"
    else:
        t = "js"
    
    return "{type}{instance}".format(type=t, instance=instance)


def get_device(device):
    return devices[device]
    
def build_button_map(device,button, name):

    if (device in button_array):
        button_array[device].update( {button:name } )
    else:
        button_array.update({
            device : {
                button : name
            }
        })


def update_joystick_dictionary(device, mode, inherit, buttons):
    data = {
        "Buttons": buttons,
        "Axis": '',
        "Inherit": inherit}

    if device in joystick_dictionary:
        if mode in joystick_dictionary[device]:
            joystick_dictionary[device][mode].update(data)
        else:
            joystick_dictionary[device].update({
                    mode:   data
                        })
    else:
        joystick_dictionary.update({
            device : {
                mode:   data
                            }
        })

devices = {}
buttonArray = {}
parse = minidom.parseString(data)

joysticks = parse.getElementsByTagName('options')
mode = "Default"
for j in joysticks:
    add_device(j)

    print(j.getAttribute('type'))
    joystick = j.getAttribute('Product')
    print(j.getAttribute('instance'))
    print(j.getAttribute('Product'))

actions = parse.getElementsByTagName('actionmap')

for i in actions:

    print("-----------")
    print("Category: {}".format(process_name(i.getAttribute('name'))))

    single_actions = i.getElementsByTagName('action')

    for i in single_actions:
        name = process_name(i.getAttribute('name'))
        print(name)
        binds = i.getElementsByTagName('rebind')
        bind = binds[0].getAttribute('input')
        button = parse_bind(bind)

        if(button and button[1] is not None):
            print("Button Found: {}".format(button[1]))
            
            build_button_map(button[0]['name'], button[1], name)

        else:
            print("Button Not found {}".format(button))

        print("-----------")

    print(buttonArray)

    print(devices)

for item in button_array:
    update_joystick_dictionary(item, "Default", False, button_array[item])

print(joystick_dictionary)