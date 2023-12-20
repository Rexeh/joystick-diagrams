from pathlib import Path

from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=[f"{Path(__file__).parent.joinpath('settings.json')}"],
)


# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
