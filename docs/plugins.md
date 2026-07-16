# Joystick Diagrams - Plugins

> [!CAUTION]
> All information here is subject to change during the course of 2.0 pre-release. If you want to build a plugin based off this, please get in touch on Discord to work together.

## Parser Plugins

Version 2.0 uses a plugin system so new games can be supported without changes to the core app.

## Plugin Structure

```
plugins/
└── my_plugin/
    ├── __init__.py
    ├── main.py
    └── img/
        └── icon.ico
```

`config.py` and `settings.json` are gone. The framework handles configuration through Pydantic models now.

## main.py

`main.py` must contain a `ParserPlugin` class that inherits from `PluginInterface`. It needs two class variables:

- `plugin_meta`: static metadata (name, version, icon)
- `plugin_settings_model`: a `PluginSettings` subclass describing required paths and options. Omit this if your plugin needs no configuration.

### Minimal example

```python
from pathlib import Path
from pydantic import Field
from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface
from joystick_diagrams.plugins.plugin_settings import PluginMeta, PluginSettings


class MySettings(PluginSettings):
    source_dir: Path | None = Field(
        default=None,
        title="Source Folder",
        json_schema_extra={"is_folder": True, "default_path": "~/Saved Games"},
    )


class ParserPlugin(PluginInterface):
    plugin_meta = PluginMeta(name="My Plugin", version="1.0.0", icon_path="img/icon.ico")
    plugin_settings_model = MySettings

    def process(self) -> ProfileCollection:
        source = self.get_setting("source_dir")
        # parse files and return a ProfileCollection
        return ProfileCollection()

    def on_settings_loaded(self) -> None:
        # rebuild any internal state that depends on settings (e.g. re-create a parser)
        pass
```

## PluginMeta

`PluginMeta` is a frozen Pydantic model. Declare it as a class variable on your plugin.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Display name shown in the UI |
| `version` | `str` | Plugin version string |
| `icon_path` | `str` | Path to icon, relative to the plugin's own directory |

## PluginSettings

`PluginSettings` is a Pydantic `BaseModel` subclass. Define your path inputs and user-configurable options as fields. The framework generates the UI, persists values to disk, and computes ready state from these fields automatically.

### Field types and their UI controls

| Field type | UI control |
|---|---|
| `bool` | Checkbox |
| `str` | Text input |
| `Path` | Folder / file browse button (required) |
| `Path \| None` | Folder / file browse button (optional) |

### Path field options (`json_schema_extra`)

| Key | Type | Default | Description |
|---|---|---|---|
| `is_folder` | `bool` | `True` | `True` shows a folder dialog, `False` shows a file dialog |
| `default_path` | `str` | | Starting directory for the browse dialog |
| `extensions` | `list[str]` | | Allowed file extensions for file browse (e.g. `[".xml"]`) |
| `required` | `bool` | `True` | If `True`, the plugin is not ready until this path is set |

### Ready state

A plugin is ready when every required `Path` field in its `PluginSettings` has a value. You don't need to implement this yourself.

## Plugin lifecycle

### process()

Called by the framework when it needs results from your plugin. Must return a `ProfileCollection`.

### on_settings_loaded()

Called after settings are restored from disk. Override this if you need to rebuild internal state from the loaded values, for example re-creating a parser instance with an updated file path.

### save_plugin_state() / load_settings()

Both are handled by the framework. Don't call them yourself. Settings are persisted as `data.json` in the plugin's AppData directory.

## Settings access

| Method | Description |
|---|---|
| `self.get_setting("field_name")` | Returns the current value of a setting |
| `self.update_setting("field_name", value)` | Updates a value and persists to disk |

## Plugin data directory

| Method | Description |
|---|---|
| `self.get_plugin_data_path()` | Returns the full path to the plugin's AppData directory |
| `self.get_plugin_data()` | Returns all files/folders in the plugin's AppData directory as `list[Path]` |

## Exception helpers

Raise these from `process()` when path validation fails:

| Method | Exception raised |
|---|---|
| `self.file_not_valid_exception("message")` | `FileNotValidError` |
| `self.directory_not_valid_exception("message")` | `DirectoryNotValidError` |
| `self.file_type_invalid("message")` | `FileTypeInvalidError` |

## Example Plugin

A working example is in the repository at `joystick_diagrams/plugins/Example/example_plugin/`.

## 3rd Party Modules

Plugins can only use standard library packages or dependencies already pulled in by first-party plugins. If you need something else, open a discussion.
