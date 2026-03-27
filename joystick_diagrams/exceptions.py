class JoystickDiagramsError(Exception):
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)


# -----------------------------------------------------------------------------
# Plugin file loading exceptions
# -----------------------------------------------------------------------------


class DirectoryNotValidError(JoystickDiagramsError):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)


class FileNotValidError(JoystickDiagramsError):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)

    def __str__(self) -> str:
        return repr("File was invalid: " + self.value)


class FileTypeInvalidError(JoystickDiagramsError):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)


class PathPermissionError(JoystickDiagramsError):
    def __init__(self, path: str = "", operation: str = "access") -> None:
        self.path = path
        self.operation = operation
        super().__init__(
            f"Permission denied: cannot {operation} '{path}'. "
            f"Try running as administrator, or choose a location your user account can access."
        )


class ExportError(JoystickDiagramsError):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)


# -----------------------------------------------------------------------------
# Plugin Exceptions
# -----------------------------------------------------------------------------


class PluginNotValidError(JoystickDiagramsError):
    def __init__(self, value: str = "", error: str = "") -> None:
        super().__init__(value)
        self.error = error

    def __str__(self) -> str:
        return repr(f"Plugin {self.value} loaded was invalid: {self.error}")


class NoPluginsExistError(JoystickDiagramsError):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)

    def __str__(self) -> str:
        return repr("No plugins were found in plugins directory")
