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

The Windows installer needs Inno Setup 6. `make build-installer` looks for it at
`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`; override with `make build-installer ISCC=<path>`.
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

# Developer Documentation
This is still work in progress, if you have any questions get in touch on Discord.

- Plugins Development [(LINK)](./plugins.md)
- Input library  [(LINK)](./profiles.md)
