import sys
from typing import Type, Sequence
from .protocol import ApplicationProtocol, LINE_WAITTIME
from .utils import force_kill


class AppClassManagerClass:
    """Register and creation of the `Application` with` the given name."""

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

    def is_registered(self, name: str) -> bool:
        return name in self._app_types

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

    def __init__(self, command: str | None = None, line_suffix: str = "\r\n"):
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

    def make_lines(self, input_str: str) -> Sequence[str | LINE_WAITTIME]:
        """Modify the command before sending to `terminal`"""
        raw_lines = [line.rstrip("\r") for line in input_str.split("\n")]
        joined_lines: list[str] = []
        buffer = ""
        continuation_chars = {"\\", "^", "`"}
        for line in raw_lines:
            stripped = line.rstrip()
            if stripped and stripped[-1] in continuation_chars:
                # 継続文字を削除して空白を追加
                buffer += stripped[:-1] + " "
            else:
                buffer += stripped
                joined_lines.append(buffer)
                buffer = ""

        if buffer:
            joined_lines.append(buffer)

        joined_lines.append("")  # 最後にEnter
        return joined_lines

    def interrupt(self, pid: int, children_pids: list[int]):
        _ = children_pids
        """Interrupt the process.
        """
        _ = pid
        for child in children_pids:
            force_kill(child)

    def filter(self, lines: Sequence[str]) -> Sequence[str]:
        return lines

    def _get_default_shell_command(self) -> str:
        if sys.platform == "win32":
            return self.WIN_DEFAULT_SHELL_COMMAND
        else:
            return self.LINUX_DEFAULT_SHELL_COMMAND
