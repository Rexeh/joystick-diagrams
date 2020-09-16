# Joystick Diagrams - Visualise your binds

!(https://travis-ci.com/Rexeh/joystick-diagrams.svg?branch=master)

## What is this tool for?
Learning flight simulators is a daunting task, with lots of buttons to remember. I built this tool for myself, and then thought others might also enjoy it, automating what is a time consuming task!

- Export your joystick/throttle/custom HID buttons to a SVG, and print with your browser
- Overlay your buttons onto an actual Joystick profile/picture
- Learn your joystick setup easier and be a better pilot!

![Image of exported profile](https://i.imgur.com/8RWBuNM.png)

## What's supported?

### General
- Custom SVG templates can be built to suit your joystick, throttle, custom HID device

### Joystick Gremlin
- Importing/inheriance of base templates into button profile exports
- Support for multiple profiles in Joystick Gremlin

### What's not supported (yet)
- POV hats (In POV mode)
- AXIS support

### Support for other games
I'm currently working on DCS World - if you have a game you think will benefit from this, let me know and I might add it.

## Installation
None required, use the supplied binary in latest release.

Run joystick-diagram.exe

### From Source
Want to run from source? You'll need Python 3.8+
Use setup.py to get up and running

## Bugs
This is an initial release, all of the templates are new and there may be configuration differences to work out.

I'm expecting issues with the Virpil templates, as don't have the logical buttons available to me.

## Usage
- Run joystick-diagram.exe
- Select your Joystick Gremlin profile XML
- Hit Export
- If it finds a match, it'll export the bindings for this device, and any modes you have configured
- Files will be stored in /diagrams when export has been completed. You can open these in a web browser, and print to PDF/printer from there

# Templates/Supported Joysticks
[Please read the about templates here](templates/readme.md)

# Support / Beer fund

## Discord
If you have any issues/questions, pop along to discord - https://discord.gg/JC5QFMB

## Beer
I plan to expand this out and continue on this journey. I'd appreciate any donations for time saved and to help me continue to support this program.
[Donate via Paypal](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url)


