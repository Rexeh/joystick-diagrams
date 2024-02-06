import logging
from abc import ABC, abstractmethod
from pathlib import Path

import dynaconf

from joystick_diagrams.exceptions import (
    DirectoryNotValid,
    FileNotValid,
    FileTypeInvalid,
)
from joystick_diagrams.input.profile_collection import ProfileCollection

_logger = logging.getLogger(__name__)


class PluginInterface(ABC):
    class FolderPath:
        def __init__(self, dialog_title: str, default_path: str):
            self.dialog_title = dialog_title
            self.default_path = default_path

    class FilePath:
        def __init__(self, dialog_title: str, default_path: str, supported_extensions: list[str]):
            self.dialog_title = dialog_title
            self.supported_extensions = supported_extensions
            self.default_path = default_path

    settings: dynaconf.LazySettings
    path: Path | None

    @property
    @abstractmethod
    def path_type(self) -> FolderPath | FilePath:
        """Returns a valid path type object to specify the plugins path sourcing method."""
        ...

    def file_not_valid_exception(self, exception_message: str):
        return FileNotValid(value=exception_message)

    def directory_not_valid_exception(self, exception_message: str):
        return DirectoryNotValid(value=exception_message)

    def file_type_invalid(self, exception_message: str):
        return FileTypeInvalid(value=exception_message)

    @abstractmethod
    def process(self) -> ProfileCollection:
        """Runs the relevant processes to return an ProfileCollection object

        Returns ProfileCollection()
        """
        ...

    @abstractmethod
    def set_path(self, path: Path) -> bool:
        """Sets the file/directory path for plugin. Plugin is responsibile for validation of Path.

        Returns Bool for success state of path set.
        """
        ...

    @abstractmethod
    def load_settings(self) -> None:
        """Loads a plugins settings"""
        ...

    @property
    def name(self) -> str:
        """Returns a plugins name property"""
        return f"{self.settings.PLUGIN_NAME}"

    @property
    def version(self) -> str:
        """Returns a valid path type object""" """Returns a version property"""
        return f"{self.settings.VERSION}"

    @property
    @abstractmethod
    def icon(self) -> str:
        """Returns a path string to plugins icon file"""
        ...

    @property
    def get_path(self) -> Path | None:
        """Returns a plugins current path"""
        return Path(self.path) if self.path else None
