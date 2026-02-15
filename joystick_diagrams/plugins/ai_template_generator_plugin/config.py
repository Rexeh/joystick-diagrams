from pathlib import Path

from dynaconf import Dynaconf, Validator  # type: ignore

settings = Dynaconf(
    settings_files=[f"{Path(__file__).parent.joinpath('settings.json')}"],
)

settings.validators.register(
    Validator("PLUGIN_NAME", required=True),
    Validator("PLUGIN_ICON", required=True),
    Validator("VERSION", required=True),
)
