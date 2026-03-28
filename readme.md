# Joystick Diagrams

<div align="center">

  ![Joystick Diagrams Logo](https://joystick-diagrams.com/img/logo.png)

  [![Release](https://img.shields.io/github/v/release/Rexeh/joystick-diagrams?include_prereleases&style=flat-square)](https://github.com/Rexeh/joystick-diagrams/releases)
  [![License](https://img.shields.io/github/license/Rexeh/joystick-diagrams?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/blob/main/LICENSE)
  [![GitHub Stars](https://img.shields.io/github/stars/Rexeh/joystick-diagrams?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/stargazers)
  [![GitHub Issues](https://img.shields.io/github/issues/Rexeh/joystick-diagrams?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/issues)
  [![Downloads](https://img.shields.io/github/downloads/Rexeh/joystick-diagrams/total?style=flat-square)](https://github.com/Rexeh/joystick-diagrams/releases)
  ![Discord](https://img.shields.io/discord/733253732355276800?label=Discord)

  **Your bindings, visualized in seconds.**

  Automatically create hardware-accurate visual reference cards for your HOTAS setup, directly from your game configuration files.

  [Download Free](https://github.com/Rexeh/joystick-diagrams/releases) · [Documentation](https://joystick-diagrams.com/setup/) · [Report Bug](https://github.com/Rexeh/joystick-diagrams/issues) · [Request Feature](https://discord.com/channels/733253732355276800/1212843539223027753)

</div>

---

## What is Joystick Diagrams?

Joystick Diagrams reads your game config files and generates hardware-accurate visual diagrams of every button, axis, hat switch, and modifier on your controllers.

No manual data entry. No design skills needed. Always in sync with your actual bindings.

**If you've ever found yourself:**
- Memorizing bindings through repetition
- Building reference cards in PowerPoint or Photoshop by hand
- Printing ugly, unreadable binding lists from the game settings
- Pausing mid-flight to check which button does what

...this is what I built it to fix.

## Supported Games

| Game | Import Type |
|------|-------------|
| **DCS World** | Per-aircraft profiles |
| **Microsoft Flight Simulator 2020** | Controller bindings |
| **Star Citizen** | Action maps |
| **IL-2 Sturmovik: Great Battles** | Controller bindings |
| **Joystick Gremlin** | Macro profiles (covers any game) |

More games can be added through the open plugin system.

## Hardware Templates

46+ SVG templates matching the exact physical layout of real HOTAS hardware. Bindings show up on the diagram right where the button sits on the actual device.

| Manufacturer | Devices |
|-------------|---------|
| **Virpil Controls** | Constellation ALPHA (L/R/Prime), MT-50CM2 Stick & Throttle, WarBRD, VFX, Control Panel |
| **WinWing** | Orion2 (F-16, F-18, F-15EX), URSA MINOR, Super Taurus Throttle, ICP, MFD, UFC, HUD panels |
| **VKB Sim** | Gladiator NXT (L/R) |
| **Thrustmaster** | Warthog Joystick & Throttle, T.16000M Joystick (L/R) & Throttle |
| **Saitek/Logitech** | X52, X56 H.O.T.A.S. (Stick & Throttle), X56 Rhino |
| **CH Products** | Fighterstick, Pro Throttle |
| **Total Controls** | Apache MPD, Multi-Function Button Box |

A starter template is included for creating custom device layouts using [draw.io](https://www.drawio.com/).

## Features

- **Automatic Binding Import.** Point the app at your game's config folder and every binding is extracted. Change a binding in-game, re-run the export, done.
- **Hardware-Accurate Diagrams.** 46+ templates matching real HOTAS hardware layouts. Glance at the diagram and know exactly which physical button does what.
- **Custom Labels.** Override verbose game action names with your own text. "Weapon Fire Primary Mode Toggle" becomes "Guns".
- **SVG & PNG Export.** SVG for print-quality output at any size. PNG at 2x resolution for sharing on Discord, forums, or as stream overlays.
- **Batch Export.** Select multiple profiles and devices, export them all at once. Regenerate all your aircraft diagrams in seconds.
- **Profile Inheritance.** Set parent profiles so common bindings carry through. Only document the differences per aircraft.
- **Device Management.** Hide devices you don't need for a particular aircraft. Manage visibility from Settings.
- **Plugin Architecture.** Open plugin system for adding new game support. Community can contribute parsers for new titles.

## How It Works

1. **Setup.** Install the app, add your game plugins, point each at the game's config folder. Profiles and devices are discovered automatically.
2. **Customise.** Browse profiles by game and aircraft. Rename actions with custom labels. Hide devices you don't need.
3. **Export.** Pick your profiles, choose a template for each device, select SVG or PNG, hit Export. Diagrams land in your chosen folder.

## Installation

### Windows

1. Download the latest [release](https://github.com/Rexeh/joystick-diagrams/releases)
2. Unzip to your preferred location
3. Launch `Joystick Diagrams.exe`

For setup guidance, see the [documentation](https://joystick-diagrams.com/setup/).

### Building from Source

```bash
git clone https://github.com/Rexeh/joystick-diagrams.git
cd joystick-diagrams
poetry install
```

## Community

- **Discord.** Join the [Joystick Diagrams Discord](https://discord.gg/JC5QFMB) for support, template sharing, and feature requests.
- **Issues.** Report bugs via [GitHub Issues](https://github.com/Rexeh/joystick-diagrams/issues).
- **Templates.** Community members contribute new device templates regularly.

## Contributing

Contributions are welcome: new device templates, game plugins, bug fixes, documentation. Open a PR or start a conversation on Discord.

## License

Distributed under the GPL-2.0 License. See [LICENSE](LICENSE) for more information.
