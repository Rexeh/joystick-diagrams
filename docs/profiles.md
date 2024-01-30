# Joystick Diagrams - ProfileCollections, Profiles, Inputs

All ParserPlugins must result in a ProfileCollection, which is part of the Joystick Diagrams Input library containing

- ProfileCollection - *A container for profiles*
- Profile - *A container for devices and inputs*

## Profile
A profile is a representation of a group of device/input configurations, as an example in DCS World a "Profile" would be a specific Airframe I.e. "A10-Cii"

A profile results in 1 or more diagrams, dependant on the number of devices contained within.

A profile has only two properties
- name (the name of your profile displayed to users)
- devices (the device dictionary for a given profile)

**Direct modification of the device dictionary should not be done, instead using  the correct add_device, get_device methods.**

### Profile Merging (Profile Inheritance)
By default, the recommendation is for Parsers to not merge profiles at source, as the UI has user functionality to do this. However in some circumstances it may make sense to merge ProfileA+ProfileB, for example if the particular game/tool has its own feature for inherited profiles (E.g. Joystick Gremlin)

For this, a helper method is provided **merge_profiles()** which allows an instance A of Profile, to absorb another Instance B's devices, inputs and modifiers.

So **InstanceA.merge_profile(instanceB: Profile_)** will result in ProfileB acting as the BASE profile, which ProfileA being layered on top resulting in a diff.

Users can further apply multiple parents on top of a given Profile via the UI.

## Inputs
In order to generate a profile, devices must be added. On a given Device_ object inputs can then be added, which are automatically maintained / overwritten. From a Plugin perspective you can simply write inputs/modifiers in any order.

### Input
The input module is not intended to be used directly, instead via the Device_ class methods such as **create_input()** and **add_modifier_to_input()**

As part of these methods, there are a number of supported Control inputs which need to be supplied as arguments.

- Button (Basic button control with ID)
- Hat (Hat Control with support for 8 way hats)
- Axis (Axis type with support for all AXIS types)
- AxisSlider (Axis type for slider controls)

The library will handle de-duplication automatically




