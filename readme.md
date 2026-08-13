# Joystick Diagrams (ENGINE)

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

## Supported Games/Tools
We have a fully documented API to build your own support for games and tools as well as special export capabilities.

- **DCS World**
- **Microsoft Flight Simulator 2020**
- **Star Citizen**
- **IL-2 Sturmovik: Great Battles**
- **Joystick Gremlin**
- **Elite Dangerous**
- **Falcon BMS**
- **OpenKneeboard**

More games can be added through the open plugin system, which is documented at https://www.joystick-diagrams.com/developers

## Hardware Templates

A number of manufacturers and devices are supported out of the box. If yours is missing then you can make your own in no time at all.

Full coverage of templates available at https://www.joystick-diagrams.com/templates/

Example of what we have!

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

## How It Works

1. **Setup.** Install the app, add your game plugins, point each at the game's config folder. Profiles and devices are discovered automatically.
2. **Customise.** Browse profiles by game and aircraft. Rename actions with custom labels. Hide devices you don't need.
3. **Export.** Pick your profiles, choose a template for each device, select SVG or PNG, hit Export. Diagrams land in your chosen folder.

## Installation

### Windows

1. Download the latest [release](https://github.com/Rexeh/joystick-diagrams/releases)
2. Unzip to your preferred location
3. Run installer, and launch application

### Linux

1. Download the `joystick-diagrams-<version>-linux-x86_64.tar.gz` from the latest [release](https://github.com/Rexeh/joystick-diagrams/releases)
2. Extract it to your preferred location
3. Run `./run.sh` from the extracted folder

There is no installer on Linux. Optionally run `./install-desktop.sh` to add an
application menu entry for your user (re-run it if you move the folder).

For setup guidance, see the [documentation](https://joystick-diagrams.com/setup/).

### Building from Source

```bash
git clone https://github.com/Rexeh/joystick-diagrams.git
cd joystick-diagrams
uv sync
```

## Community

- **Discord.** Join the [Joystick Diagrams Discord](https://discord.gg/JC5QFMB) for support, template sharing, and feature requests.
- **Issues.** Report bugs via [GitHub Issues](https://github.com/Rexeh/joystick-diagrams/issues).
- **Templates.** Community members contribute new device templates regularly.

## Contributing

Contributions are welcome: new device templates, game plugins, bug fixes, documentation. Open a PR or start a conversation on Discord.

### Device Templates
Creating these is at the mercy of either owning the device, or the community creating them for others. The biggest help to the project would be increasing our library of templates, and improving the ones we have.

## License

Distributed under the GPL-2.0 License. See [LICENSE](LICENSE) for more information.
