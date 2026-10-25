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

More games can be added through the open plugin system (in the app, games are added in 1. Setup), which is documented at https://www.joystick-diagrams.com/developers

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

A Starter Template is included for creating your own templates using [draw.io](https://www.drawio.com/); the template picker can copy it for any controller.

## How It Works

The app is four stages, left to right along the top. Nothing is locked: you can open any stage at any time, and the button at the bottom right always says what to do next.

1. **Setup.** Tick the games you play. For each one, confirm the folder where it keeps your bindings (the app suggests the usual places, such as DCS World's Saved Games folder). The app reads your bindings and shows what it found: how many controllers and profiles, and which controllers need a template.
2. **Controllers.** Choose a template for each controller: a picture of it with a box for each control. The template picker shows how many of the controls you use are on each template, so you can see a good fit at a glance. If yours isn't there, start from the Starter Template or use a template file of your own. A controller with nothing bound (or one the game lists as a keyboard or mouse) is set to **No diagram**; you can change that.
3. **Bindings.** Optional. Check which action is on each control, give long actions a shorter **label** for your diagrams (your game isn't changed), and let one profile use another's bindings (**Shared bindings**, such as a Common profile).
4. **Diagrams.** Lands on **Export**, with every ready profile ticked. Choose PNG, PDF or SVG and press Export. The first time, the app asks where to save your diagrams and remembers the folder. The result shows inline, with anything worth checking before you print. **Make changes** holds **Appearance** (fonts, colours, modifier colours), **Layout** (move, resize or add boxes, per controller) and **Pages** (two or more controllers on one sheet, such as stick and throttle on one A4 or kneeboard page; one file per profile, by default for the profiles that use all of them).

After the first run the app opens on the stage you last used and reads your games again in the background, so changed bindings show up on their own (turn this off in Settings). Exporting while it reads waits for the read to finish.

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
