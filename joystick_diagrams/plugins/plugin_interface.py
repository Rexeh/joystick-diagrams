from abc import ABC, abstractmethod
from pathlib import Path

import dynaconf

import joystick_diagrams.exceptions as JDException


class PluginInterface(ABC):
    settings: dynaconf.LazySettings

    def file_not_valid_exception(self, exceptionMessage: str):
        return JDException.FileNotValid(value=exceptionMessage)

    def directory_not_valid_exception(self, exceptionMessage: str):
        return JDException.DirectoryNotValid(value=exceptionMessage)

    def FileTypeInvalid(self, exceptionMessage: str):
        return JDException.FileTypeInvalid(value=exceptionMessage)

    @abstractmethod
    def process(self) -> int:
        """
        Runs the relevant processes to return an InputCollection

        Returns InputCollection()
        """
        ...

    @abstractmethod
    def set_path(self, path: Path) -> bool:
        """
        Sets the file/directory path for plugin. Plugin is responsibile for validation of Path.

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
