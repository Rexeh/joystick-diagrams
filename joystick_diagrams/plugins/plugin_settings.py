from pydantic import BaseModel, ConfigDict


class PluginMeta(BaseModel):
    """Required static metadata every plugin must declare as a class variable.

    Example:
        class ParserPlugin(PluginInterface):
            plugin_meta = PluginMeta(name="My Plugin", version="1.0.0", icon_path="img/icon.ico")
    """

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    icon_path: str  # relative path from the plugin's own directory (e.g. "img/dcs.ico")


class PluginSettings(BaseModel):
    """Base class for plugin settings, including paths and user-configurable options.

    Subclass and attach to a plugin via the ``plugin_settings_model`` class variable:

        class MySettings(PluginSettings):
            # Required path — plugin won't be ready until this is set
            input_file: Path = Field(
                default=None,
                title="Input File",
                json_schema_extra={"is_folder": False, "default_path": "~/Documents", "extensions": [".xml"]}
            )
            # Optional path
            extra_dir: Path | None = Field(
                default=None,
                title="Extra Directory (optional)",
                json_schema_extra={"is_folder": True, "required": False}
            )
            # Regular settings
            enable_feature: bool = Field(default=True, title="Enable Feature")
            custom_label: str = Field(default="", title="Custom Label")

        class ParserPlugin(PluginInterface):
            plugin_settings_model = MySettings

    Path field json_schema_extra options:
      - is_folder (bool, default True)  — folder browse vs file browse dialog
      - default_path (str)              — starting directory for the browse dialog
      - extensions (list[str])          — allowed extensions for file browse (e.g. [".xml"])
      - required (bool, default True)   — if True, plugin is not ready until this path is set

    The framework handles persistence (data.json), UI generation, and ready-state
    computation automatically. Supported field types and their generated controls:
      - bool       → QCheckBox
      - str        → QLineEdit
      - Path       → folder/file browse button
      - Path | None → folder/file browse button (optional)
    """

    model_config = ConfigDict(validate_assignment=True)
