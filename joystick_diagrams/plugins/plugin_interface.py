from abc import ABC, abstractmethod
from pathlib import Path

import dynaconf

import joystick_diagrams.exceptions as JDException
from joystick_diagrams.input.profile_collection import ProfileCollection


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
    path: str

    @property
    @abstractmethod
    def path_type(self) -> FolderPath | FilePath:
        ...

    def file_not_valid_exception(self, exception_message: str):
        return JDException.FileNotValid(value=exception_message)

    def directory_not_valid_exception(self, exception_message: str):
        return JDException.DirectoryNotValid(value=exception_message)

    def file_type_invalid(self, exception_message: str):
        return JDException.FileTypeInvalid(value=exception_message)

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

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @property
    @abstractmethod
    def icon(self) -> str:
        ...
