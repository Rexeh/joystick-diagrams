class JoystickDiagramsException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class directory_not_valid(JoystickDiagramsException):
    def __init__(self, value):
        super().__init__(value)


class file_not_valid(JoystickDiagramsException):
    def __init__(self, value=""):
        super().__init__(value)

    def __str__(self):
        return repr("File was invalid: " + self.value)


class file_type_invalid(JoystickDiagramsException):
    def __init__(self, value="Default"):
        super().__init__(value)
