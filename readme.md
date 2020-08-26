# Joystick Diagrams - Visualise your binds

This is an initial release - Please raise bugs/feature requests to help me improve it.

## What is this tool for?

Learning simulators is a daunting task, with lots of buttons to remember. If only there was some easy way to print out what my bindings are... onto a pretty picture of my stick!

Now there is. 

- Export your joystick/throttle/custom HID buttons to a SVG, and print with your browser
- Overlay your buttons onto an actual Joystick profile/picture

## What's supported?

### Joystick Gremlin
- Custom SVG templates can be built to suit your joystick, throttle, custom HID device
- Support for multiple profiles in Joystick Gremlin

## What's not supported

### Joystick Gremlin
Please get in touch with me if these are of importance to you to use the software
- Importing/inheriance of base templates into button profile exports (In progress)
- POV hats (In POV mode) - If your POV is configured for button outputs, then it will work

### Support for other programs/games (On the roadmap)
- DCS World
- IL2
- Etc
- Please suggest games you'd think this would be useful for

## Installation

### Prerequisites
Requires Python 3.7
- No install required, direct execution via Python

"py main.py"

## Usage

Please ensure you have **backup of your config**, this should not modify if but I also take no responsibility if you lose all your binds!

- Edit Config.py to point to your Joystick Gremlin config file you want to map
- Program will try match Device Names, with available files in /templates
- If it finds a match, it'll export the bindings for this device, and any modes you have configured
- If you have web browser enabled, they'll automatically open in your browser
- Files will be stored in /diagrams when export has been completed. You can open these in a web browser, and print to PDF/printer from there

# Templates/Supported Devices
[Please read](templates/readme.md)

## Limitations
- If your binding overlaps/wraps on export against your design, adjust your SVG image. The program will not automatically change your design to fit content
- Highly configurable joysticks/throttles (I.e. Virpil) may need template customisation. As button 1 etc may differ from someone elses button 1

## Support / Beer fund
I plan to expand this out and continue on this journey. I'd appreciate any donations for time saved and to help me continue to support this program.

[Donate via Paypal](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url)


