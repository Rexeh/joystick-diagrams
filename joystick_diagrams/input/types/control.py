from abc import ABC, abstractmethod


class JoystickDiagramControl(ABC):
    @property
    @abstractmethod
    def identifier(self):
        ...
