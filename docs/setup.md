# Development
The tool is currently undergoing a V2 release, so major changes will be taking place, for any development questions or to help out with development get in touch.

## Prerequisites
- uv (https://docs.astral.sh/uv/)
- Python 3.11 x64

## Repository Setup

1. Install uv for your system (https://docs.astral.sh/uv/getting-started/installation/)
2. Run **uv sync**

You should now have the relevant things installed to develop Joystick Diagrams, if you run into any issues join our Discord server for support.

## Building executables
The easiest way to do this is via Make (https://gnuwin32.sourceforge.net/packages/make.htm), and using the included MakeFile.

| Target | Platform | Output |
| --- | --- | --- |
| `make build-app` | Any | Frozen standalone binary package in **/build/app** |
| `make build-installer` | Windows | The above, plus the Inno Setup installer in **/installer/Output** |
| `make build-tarball` | Linux | The above, plus a `.tar.gz` in **/dist** |
| `make build-exe` | Windows | Alias for `build-installer` (the historic target name) |

The Windows installer needs Inno Setup 6. `make build-installer` shells out to
`packaging\windows\build_installer.bat`, which looks for `ISCC.exe` at the default
install location and then on PATH; override with `make build-installer ISCC=<path>`.
The installer version is taken from `version_manifest.json`, so run `make make-version`
(or any of the build targets, which depend on it) after bumping the version.

>  [!NOTE]
>  Builds must take place on the target OS - there is no cross compilation. Linux ships
>  as a tarball rather than an installer; users extract it and run `./run.sh`. The Linux
>  packaging files live in **/packaging/linux**.

### Building in CI
The **Python package** workflow (`.github/workflows/python-package.yml`) is manually
triggered (`workflow_dispatch`) and builds both platforms, producing three artifacts:
`windows-installer`, `windows-portable` and `linux-tarball`. Releases are still published
by hand from those artifacts.

# Using the app: the four stages
The window is a strip of four stages, **1. Setup › 2. Controllers › 3. Bindings › 4. Diagrams**,
with a cog for Settings at the end. Each stage shows a one-line status under its name; the
pinned footer shows the next step. No stage is ever locked.

| Stage | What happens there | Code |
| --- | --- | --- |
| 1. Setup | Choose games (first launch: "Which games do you play?"), confirm each game's folder (`PluginInterface.suggested_paths()` candidates, or Browse), read, results card | `ui/setup_page.py`, `ui/strings_setup.py` |
| 2. Controllers | Groups: Needs a template / Ready / No diagram / Not in your latest bindings; the template picker (fit counts on every row, Starter Template copy, file picker) | `ui/controllers_page.py`, `ui/template_picker.py`, `ui/strings_controllers.py` |
| 3. Bindings | Bindings, Shared bindings, Labels | `ui/bindings_page.py`, `ui/strings_bindings.py` |
| 4. Diagrams | Export (lands here), then Make changes: Appearance, Layout, Pages | `ui/diagrams_page.py`, `ui/export_page.py`, `ui/strings_diagrams.py` |

Behaviour worth knowing when testing:

- **Landing.** No game set up → 1. Setup. Otherwise the stage used last.
- **Auto-read on launch.** On by default (Settings › General › "Read my games each time
  the app opens"). It runs in the background, never blocks and never opens a dialog;
  tab 1 shows "Reading…", a failure turns tab 1 amber with a banner.
- **Export folder.** There is no default. The first export asks once (pre-filled with a
  suggestion), the folder is remembered, and it is asked again only if it disappears.
  While a read is running, Export waits and starts by itself when the read finishes.
- **No diagram.** Set automatically only when nothing is bound after merging, or when the
  game declares the controller a keyboard or mouse (`Profile_.add_device(..., device_type=...)`,
  see [plugins.md](./plugins.md)). The reason shown on every screen comes from
  `device_status.reason_text`.
- **Layouts** are stored per template *and* controller, so two controllers on the same
  Starter Template keep separate box positions.
- **Pages** put two or more controllers on one sheet (side by side, stacked or grid; A4,
  Letter, Kneeboard 5.5×8.5in, Fit to content or Custom). "Make this page for" picks the
  profiles (`Page.profile_rule`): by default only profiles in which every controller on
  the page has bindings; "Any profile that uses one of them" also makes the others, with
  a controller that has no bindings there drawn dimmed with "No bindings in <profile>".
  The Combine dialog shows live counts and the list of profiles; the Export list shows
  one row per profile under the page.
- **Folder candidates** in 1. Setup show "Last changed <date>" but no profile count
  (counting needs a full read).
- **Words.** Every user-facing string lives in a `ui/strings_*.py` module and follows the
  language guide (game, controller, binding, template, box, label, profile, style,
  diagram, page). `tests/ui/test_f2_strings_language.py` fails on banned words.

Sample data for a manual walkthrough: [tests/data/sample_profiles](../tests/data/sample_profiles/README.md).

# Developer Documentation
This is still work in progress, if you have any questions get in touch on Discord.

- Plugins Development [(LINK)](./plugins.md)
- Input library  [(LINK)](./profiles.md)
