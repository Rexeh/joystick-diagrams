from joystick_diagrams.plugin_manager import ParserPluginManager, PluginInterface


class appState:
    """

    appState for managing shared data for application.

    """

    _inst = None

    def __new__(cls, *args, **kwargs):
        if not cls._inst:
            cls._inst = super(appState, cls).__new__(cls, *args, **kwargs)
            cls._inst._init()
        return cls._inst

    def _init(self) -> None:
        self.plugin_manager: ParserPluginManager | None = None
        self.other: str | None = None

    def init_plugins(self, plugin_manager: ParserPluginManager):
        self.plugin_manager = plugin_manager

    def init_other(self):
        print("Running func")
        self.other = "1223"
