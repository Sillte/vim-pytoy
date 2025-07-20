import sys
from .protocol import ApplicationProtocol
from .utils import force_kill, send_ctrl_c
from typing import Type

class AppClassManagerClass:
    """Register and creation of the `Application` with` the given name.

    """
    def __init__(self):
        self._app_types: dict[str, Type[ApplicationProtocol]] = {}

    @property
    def app_types(self) -> dict[str, Type[ApplicationProtocol]]:
        return self._app_types

    def register(self, name: str):
        def _inner(application_cls: Type[ApplicationProtocol]):
            self._app_types[name] = application_cls
            return application_cls
        return _inner

    @property
    def app_names(self) -> list[str]:
        return list(self.app_types.keys())

    def create(self, name: str, **kwargs) -> ApplicationProtocol:
        return self.app_types[name](**kwargs)

AppManager = AppClassManagerClass()



# Below is the example of applications.

DEFAULT_SHELL_APPLICATION_NAME = "shell"

@AppManager.register(name=DEFAULT_SHELL_APPLICATION_NAME)
class ShellApplication(ApplicationProtocol):
    WIN_DEFAULT_SHELL_COMMAND = "cmd.exe"
    LINUX_DEFAULT_SHELL_COMMAND = "bash"

    def __init__(self, command: str | None = None , line_suffix: str="\r\n"):
        if command is None:
            command = self._get_default_shell_command()
        self._command = command
        self._line_suffix = line_suffix

    @property
    def command(self) -> str:
        return self._command 

    def is_busy(self, children_pids: list[int], lastline: str) -> bool:
        _ = lastline
        return bool(children_pids)

    def make_lines(self, input_str: str) -> list[str]: 
        """Modify the command before sending to `terminal`
        """
        lines = input_str.split("\n")
        return [line.strip("\r") for line in lines] + [""]

    def interrupt(self, pid: int, children_pids: list[int]):
        _ = children_pids
        """Interrupt the process.
        """
        _ = pid
        for child in children_pids:
            force_kill(child)

    def _get_default_shell_command(self) -> str:
        if sys.platform == "win32":
            return self.WIN_DEFAULT_SHELL_COMMAND
        else:
            return self.LINUX_DEFAULT_SHELL_COMMAND


