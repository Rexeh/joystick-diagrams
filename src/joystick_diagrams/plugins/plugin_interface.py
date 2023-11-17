from abc import ABC, abstractmethod, abstractproperty


class PluginInterface(ABC):
    @abstractmethod
    def process(self) -> int:
        ...

    @abstractmethod
    def init(self) -> bool:
        ...

    @abstractmethod
    def load(self) -> list:
        ...

    @abstractproperty
    def name(self) -> str:
        ...

    @abstractproperty
    def version(self) -> str:
        ...
