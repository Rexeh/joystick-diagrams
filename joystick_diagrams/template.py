"""Represents a Joystick Diagram template file format

Interacts with the template file to allow interogration of template configuration, and compatability with potential devices

"""

import functools
import logging
import os
import re
from hashlib import sha256
from pathlib import Path

from joystick_diagrams.exceptions import JoystickDiagramsError

_logger = logging.getLogger(__name__)


def bundled_templates_root() -> Path:
    """The bundled ``templates`` folder, resolved (``install_root()`` is "" in dev)."""
    from joystick_diagrams.utils import install_root

    return (Path(install_root() or ".").resolve() / "templates").resolve()


def _normcase(path: Path) -> str:
    return os.path.normcase(str(path))


def template_key_for(path: Path) -> str:
    """Stable identity for a template file (plan §4.3).

    ``bundled:<posix path relative to the bundled root>`` for shipped templates,
    so upgrades and reinstalls to another drive keep layouts; otherwise
    ``user:<resolved absolute posix path>``. Case-insensitive on Windows.
    """
    resolved = path.resolve()
    root = bundled_templates_root()
    try:
        relative = Path(_normcase(resolved)).relative_to(_normcase(root))
    except ValueError:
        return f"user:{resolved.as_posix()}"
    return f"bundled:{relative.as_posix()}"


def hash_file_bytes(path: Path) -> str:
    """sha256 of the file bytes, as ``version.generate_template_manifest`` computes it."""
    with open(path, "rb", buffering=0) as file:
        return sha256(file.read()).hexdigest()


class Template:
    BUTTON_KEY = re.compile(r"\bBUTTON_\d+\b", flags=re.IGNORECASE)

    # Modifiers
    MODIFIER_KEYS = [
        # All Modifiers Key
        re.compile(r"\b[a-zA-Z]+_\w+_Modifiers\b", flags=re.IGNORECASE),
        # Handles Modifier_X
        re.compile(r"\b[a-zA-Z]+_\w+_Modifier_\d+\b", flags=re.IGNORECASE),
        # Handles Specific Keys Modifier_X_Item
        re.compile(r"\b[a-zA-Z]+_\w+_Modifier_\d+_[a-zA-Z]+\b", flags=re.IGNORECASE),
    ]

    HAT_KEY = re.compile(r"\bPOV_\d+_[URDL]+\b", flags=re.IGNORECASE)
    AXIS_KEY = re.compile(r"\bAXIS_[a-zA-Z]+_?\d?+\b", flags=re.IGNORECASE)
    TEMPLATE_NAMING_KEY = re.compile(r"\bTEMPLATE_NAME\b", flags=re.IGNORECASE)
    TEMPLATE_DATE_KEY = re.compile(r"\bCURRENT_DATE\b", flags=re.IGNORECASE)

    def __init__(self, template_path: str):
        self.raw_data: str = self.get_template_data(Path(template_path))
        self.template_file_name = Path(template_path).name
        self.template_path: Path = Path(template_path).resolve()
        self._content_hash: tuple[tuple[int, int], str] | None = None

    @property
    def template_key(self) -> str:
        "Stable identity used to key layouts and render caches (cheap, no file read)"
        return template_key_for(self.template_path)

    @property
    def content_hash(self) -> str:
        """sha256 of the template FILE bytes, memoised by (mtime_ns, size).

        Hashes bytes rather than ``raw_data`` so it equals the version manifest
        hash for bundled templates and is stable when ``raw_data`` is reassigned.
        """
        stat = self.template_path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        if self._content_hash is None or self._content_hash[0] != stamp:
            self._content_hash = (stamp, hash_file_bytes(self.template_path))
        return self._content_hash[1]

    def get_template_data(self, template_path: Path):
        try:
            with Path(template_path).open("r", encoding="utf-8") as f:
                # TODO increased validation to check its a proper template file
                return f.read()
        except Exception as e:
            _logger.error(e)
            raise JoystickDiagramsError(
                "There was an issue reading the template file"
            ) from e

    @functools.cached_property
    def _buttons(self) -> set[str]:
        return {x.lower() for x in re.findall(self.BUTTON_KEY, self.raw_data)}

    @functools.cached_property
    def _hats(self) -> set[str]:
        return {x.lower() for x in re.findall(self.HAT_KEY, self.raw_data)}

    @functools.cached_property
    def _axis(self) -> set[str]:
        return {x.lower() for x in re.findall(self.AXIS_KEY, self.raw_data)}

    @functools.cached_property
    def _modifiers(self) -> set[str]:
        result = []
        for modifier_search_key in self.MODIFIER_KEYS:
            matches = re.findall(modifier_search_key, self.raw_data)
            result.extend(matches)
        return {x.lower() for x in result}

    def get_template_modifiers(self) -> set[str]:
        "Returns the available MODIFIER NUMBERS supported for a given CONTROL from the template"
        return self._modifiers

    def get_template_hats(self) -> set[str]:
        "Returns the available HAT controls from the template"
        return self._hats

    def get_template_axis(self) -> set[str]:
        "Returns the available AXIS controls from the template"
        return self._axis

    def get_template_buttons(self) -> set[str]:
        "Returns the available BUTTON controls from the template"
        return self._buttons

    @property
    def template_name(self) -> bool:
        "Checks if the template supports naming"
        return bool(re.search(self.TEMPLATE_NAMING_KEY, self.raw_data))

    @property
    def date(self) -> bool:
        "Checks if the template supports dating"
        return bool(re.search(self.TEMPLATE_DATE_KEY, self.raw_data))

    @property
    def button_count(self) -> int:
        "Returns the number of buttons available"
        return len(self.get_template_buttons())

    @property
    def axis_count(self) -> int:
        "Returns the number of axis available"
        return len(self.get_template_axis())

    @property
    def hat_count(self) -> int:
        "Returns the number of hats available"
        return len(self.get_template_hats())

    @property
    def modifier_count(self) -> int:
        "Returns the number of modifiers available"
        return len(self.get_template_modifiers())


if __name__ == "__main__":
    pass
