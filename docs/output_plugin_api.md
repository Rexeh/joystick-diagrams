# Output Plugin API

Output plugins are post-processing hooks that run automatically after every export. They receive the exported files, device metadata, and the full input binding model, allowing you to deliver diagrams to other tools, generate alternative output formats, or extract binding data for any purpose.

## Creating an Output Plugin

Create a directory under `joystick_diagrams/plugins/output_plugins/` with this structure:

```
output_plugins/
  your_plugin/
    __init__.py
    main.py
    img/
      icon.ico
```

`main.py` must define a class called `OutputPlugin` that inherits from `OutputPluginInterface`:

```python
from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class OutputPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(
        name="My Plugin",
        version="1.0.0",
        icon_path="img/icon.ico",
    )

    def process_export(self, results: list[ExportResult]) -> bool:
        for result in results:
            print(f"{result.profile_name} - {result.device_name}")
        return True
```

The plugin is automatically discovered and appears in Settings > Output Plugins.

## ExportResult

Every exported device produces one `ExportResult`. This is a frozen dataclass with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `profile_name` | `str` | Display name of the profile (e.g. `"A-10C II"`, `"F/A-18C Hornet"`) |
| `device_name` | `str` | Display name of the hardware device (e.g. `"Thrustmaster HOTAS Warthog Joystick"`) |
| `device_guid` | `str` | Unique device GUID |
| `source_plugin` | `str` | Name of the input parser plugin that produced this profile (e.g. `"DCS World"`, `"Star Citizen"`) |
| `template_name` | `str \| None` | SVG template filename used, or `None` |
| `export_format` | `str` | `"SVG"` or `"PNG"` |
| `file_path` | `Path` | Absolute path to the exported file (SVG or PNG depending on format) |
| `export_directory` | `Path` | Root export directory for this run |
| `device` | `Device_` | The full device model containing all inputs and bindings |

## Device Model

The `device` field on `ExportResult` gives you direct access to the parsed binding data for that device. This is the same data used to render the diagrams.

### Device_

```python
device = result.device

device.guid         # str - device GUID
device.name         # str - device display name
device.get_inputs() # dict[str, dict[str, Input_]] - inputs grouped by type
device.get_combined_inputs()  # dict[str, Input_] - all inputs in a flat dict
device.get_input(type, id)    # Input_ | None - get a specific input
```

`get_inputs()` returns a dictionary keyed by input type:

```python
{
    "buttons":     {"BUTTON_0": Input_, "BUTTON_1": Input_, ...},
    "axis":        {"AXIS_X": Input_, "AXIS_Y": Input_, ...},
    "axis_slider": {"AXIS_SLIDER_0": Input_, ...},
    "hats":        {"POV_0_U": Input_, "POV_0_D": Input_, ...},
}
```

`get_combined_inputs()` returns all inputs flattened into a single dictionary:

```python
{"BUTTON_0": Input_, "AXIS_X": Input_, "POV_0_U": Input_, ...}
```

### Input_

Each `Input_` represents a single control binding:

```python
input_obj = device.get_input("buttons", "BUTTON_0")

input_obj.identifier    # str - e.g. "BUTTON_0", "AXIS_X", "POV_0_U"
input_obj.command       # str - the bound command/action name
input_obj.modifiers     # list[Modifier] - modifier key combinations
input_obj.input_control # Button | Axis | AxisSlider | Hat - the control object
```

### Control Types

Each `input_control` is one of:

| Type | Fields | Identifier Format |
|------|--------|-------------------|
| `Button` | `id: int` | `BUTTON_{id}` |
| `Axis` | `id: AxisDirection` | `AXIS_{X\|Y\|Z\|RX\|RY\|RZ\|SLIDER}` |
| `AxisSlider` | `id: int` | `AXIS_SLIDER_{id}` |
| `Hat` | `id: int`, `direction: HatDirection` | `POV_{id}_{U\|UR\|R\|DR\|D\|DL\|L\|UL}` |

### Modifier

Modifiers represent alternative bindings when modifier keys are held:

```python
for mod in input_obj.modifiers:
    mod.modifiers  # set[str] - e.g. {"Ctrl", "Shift"}
    mod.command    # str - the command when these modifiers are active
    str(mod)       # "Fire - Ctrl+Shift"
```

## Plugin Settings

Define a Pydantic model to get auto-generated UI in the Settings page:

```python
from pathlib import Path
from pydantic import Field

class MySettings(PluginSettings):
    output_path: Path | None = Field(
        default=None,
        title="Output Folder",
        json_schema_extra={"is_folder": True, "default_path": "~/Documents"},
    )
    enabled_feature: bool = Field(
        default=True,
        title="Enable Feature",
    )
    mode: str = Field(
        default="default",
        title="Mode",
        json_schema_extra={"options": ["default", "advanced"]},
    )

class OutputPlugin(OutputPluginInterface):
    plugin_settings_model = MySettings
    ...
```

Supported field types and their generated UI controls:

| Type | UI Control |
|------|-----------|
| `Path \| None` | Folder/file browse button |
| `bool` | Checkbox |
| `str` | Text field |
| `str` with `json_schema_extra={"options": [...]}` | Dropdown (QComboBox) |

Path field `json_schema_extra` options:
- `is_folder` (bool, default `True`) - folder vs file browse dialog
- `default_path` (str) - starting directory for the browse dialog
- `extensions` (list[str]) - allowed file extensions (e.g. `[".xml"]`)
- `required` (bool, default `True`) - if `True`, plugin is not ready until this path is set

Access settings in your plugin with `self.get_setting("field_name")`. Settings are automatically persisted to JSON.

## Ready State

A plugin's `ready` property controls whether it can run. By default it returns `True` when all required `Path` fields have been set. Override it for custom logic:

```python
@property
def ready(self) -> bool:
    mode = self.get_setting("mode")
    if mode == "dcs":
        return self.get_setting("dcs_path") is not None
    return self.get_setting("output_path") is not None
```

## Lifecycle

1. Plugin is discovered at app startup from `output_plugins/` directory
2. Settings are loaded from disk and enabled state is restored from the database
3. Plugin appears in Settings > Output Plugins with an enable toggle and setup panel
4. After every export (SVG or PNG), all enabled and ready output plugins receive `process_export(results)`
5. For SVG exports: plugins run on the export worker thread
6. For PNG exports: plugins run on a separate thread pool worker after PNG conversion completes

## Example: Extracting Bindings to JSON

```python
import json
from pathlib import Path

from pydantic import Field

from joystick_diagrams.plugins.output_plugin_interface import (
    ExportResult,
    OutputPluginInterface,
)
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class BindingsExportSettings(PluginSettings):
    output_path: Path | None = Field(
        default=None,
        title="Output Folder",
        json_schema_extra={"is_folder": True, "default_path": "~/Documents"},
    )


class OutputPlugin(OutputPluginInterface):
    plugin_meta = PluginMeta(
        name="Bindings JSON Export",
        version="1.0.0",
        icon_path="img/icon.ico",
    )
    plugin_settings_model = BindingsExportSettings

    def process_export(self, results: list[ExportResult]) -> bool:
        output_path = self.get_setting("output_path")
        if output_path is None:
            return False

        for result in results:
            bindings = {}
            for input_id, input_obj in result.device.get_combined_inputs().items():
                entry = {"command": input_obj.command}
                if input_obj.modifiers:
                    entry["modifiers"] = [
                        {
                            "keys": sorted(m.modifiers),
                            "command": m.command,
                        }
                        for m in input_obj.modifiers
                    ]
                bindings[input_id] = entry

            data = {
                "profile": result.profile_name,
                "device": result.device_name,
                "source": result.source_plugin,
                "bindings": bindings,
            }

            filename = f"{result.device_guid[:5]}-{result.profile_name}.json"
            file_path = Path.joinpath(Path(output_path), filename)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        return True
```
