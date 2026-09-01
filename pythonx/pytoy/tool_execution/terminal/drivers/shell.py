from typing import Sequence

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.tool_execution.terminal.contract import (
    InputOperation,
    InterruptionCode,
    Snapshot,
    TerminalDriverProtocol,
)
from pytoy.tool_execution.terminal.infra.driver import DEFAULT_SHELL_DRIVER_NAME

driver_manager = GlobalPytoyContext().get().terminal_driver_manager


def _shell_make_operations(input_str: str) -> Sequence[str]:
    """Considering the `continuation` chars, making the
    `commands` of shell.
    """
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
    return joined_lines


@driver_manager.register("windows_cmd")
class CmdExeDriver:
    def __init__(self, kind: str = "cmd") -> None:
        self._command = "cmd.exe"
        self._kind = kind

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def command(self):
        return self._command

    @property
    def eol(self) -> str:
        # [NOTE]: This is hack. Note that the space is appended.
        # `empty` space may be necessary to
        # supprsess the peculiar `cmd.exe` behavior.
        return " \r"

    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool:
        return bool(children_pids)

    def make_operations(self, input_str: str, /) -> Sequence[InputOperation]:
        """Modify the command before sending to `terminal`"""
        return _shell_make_operations(input_str)

    def interrupt(self, pid: int, children_pids: list[int]):
        return InterruptionCode(preference="kill_tree")


@driver_manager.register(DEFAULT_SHELL_DRIVER_NAME)
class ShellDriver(TerminalDriverProtocol):
    WIN_DEFAULT_SHELL_COMMAND = "cmd.exe"
    LINUX_DEFAULT_SHELL_COMMAND = "bash"

    def __init__(self, name: str = "shell"):
        import os

        self._impl = CmdExeDriver(kind=name) if os.name == "nt" else BashDriver(name)

    @property
    def kind(self) -> str:
        return self._impl.kind

    @property
    def command(self) -> str:
        return self._impl.command

    @property
    def eol(self) -> str | None:
        return self._impl.eol

    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool | None:
        return self._impl.is_busy(children_pids, snapshot)

    def make_operations(self, input_str: str, /) -> Sequence[InputOperation]:
        return self._impl.make_operations(input_str)

    def interrupt(self, pid: int, children_pids: list[int]):
        _ = children_pids
        """Interrupt the process.
        """
        return self._impl.interrupt(pid, children_pids)


@driver_manager.register("bash")
class BashDriver:
    def __init__(self, kind: str = "bash") -> None:
        self._kind = kind
        self._command = "bash"

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def command(self):
        return self._command

    @property
    def eol(self) -> str:
        return "\n"

    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool:
        return bool(children_pids)

    def make_operations(self, input_str: str, /) -> Sequence[InputOperation]:
        """Modify the command before sending to `terminal`"""
        return _shell_make_operations(input_str)

    def interrupt(self, pid: int, children_pids: list[int]):
        return InterruptionCode(preference="kill_tree")
