class JoystickDiagramsError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


# -----------------------------------------------------------------------------
# Plugin file loading exceptions
# -----------------------------------------------------------------------------


class DirectoryNotValidError(JoystickDiagramsError):
    def __init__(self, value=""):
        super().__init__(value)


class FileNotValidError(JoystickDiagramsError):
    def __init__(self, value=""):
        super().__init__(value)

    def __str__(self):
        return repr("File was invalid: " + self.value)


class FileTypeInvalidError(JoystickDiagramsError):
    def __init__(self, value="Default"):
        super().__init__(value)


# -----------------------------------------------------------------------------
# Plugin Exceptions
# -----------------------------------------------------------------------------


class PluginNotValidError(JoystickDiagramsError):
    def __init__(self, value="", error=""):
        super().__init__(value)
        self.error = error

    def __str__(self):
        return repr(f"Plugin {self.value} loaded was invalid: {self.error}")


class NoPluginsExistError(JoystickDiagramsError):
    def __init__(self, value=""):
        super().__init__(value)

    def __str__(self):
        return repr("No plugins were found in plugins directory")
