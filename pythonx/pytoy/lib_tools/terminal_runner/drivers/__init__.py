from pytoy.lib_tools.terminal_runner.models import TerminalDriverProtocol, Snapshot, InputOperation, WaitOperation, WaitUntilOperation
from pytoy.lib_tools.terminal_runner.models import LineStr, RawStr, InterruptionCode

from pytoy.lib_tools.process_utils import force_kill
from pytoy.contexts.pytoy import GlobalPytoyContext


from typing import Sequence

DEFAULT_SHELL_DRIVER_NAME = "shell"

class TerminalDriverManager:
    def __init__(self):
        self._drivers: dict[str, type[TerminalDriverProtocol]] = {}

    def register(self, driver_name: str):
        def _wrap(driver_class: type[TerminalDriverProtocol]):
            self._drivers[driver_name] = driver_class
            return driver_class
        return _wrap
    
    def _is_registered(self, driver_name: str) -> bool:
        return driver_name in self._drivers
    
    @property
    def driver_names(self) -> list[str]:
        return list(self._drivers.keys())

    def create(self, driver_name: str, **kwargs) -> TerminalDriverProtocol:
        cls = self._drivers.get(driver_name)
        if not cls:
            raise ValueError(f"Driver {driver_name} not found")
        return cls(**kwargs)



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

driver_manager = GlobalPytoyContext().get().terminal_driver_manager

@driver_manager.register("windows_cmd")
class CmdExeDriver:
    def __init__(self, name: str = "cmd") -> None:
        self._command = "cmd.exe"
        self._name = name

    @property
    def name(self) -> str:
        return self._name
        
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



@driver_manager.register("bash")
class BashDriver:
    def __init__(self, name: str = "bash") -> None:
        self._command = "bash"
        self._name = name

    @property
    def name(self) -> str:
        return self._name
        
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


@driver_manager.register(DEFAULT_SHELL_DRIVER_NAME)
class ShellDriver(TerminalDriverProtocol):
    WIN_DEFAULT_SHELL_COMMAND = "cmd.exe"
    LINUX_DEFAULT_SHELL_COMMAND = "bash"

    def __init__(self, name: str = "shell"):
        import os 
        self._impl = CmdExeDriver(name) if os.name == "nt" else BashDriver(name)

    @property
    def name(self) -> str:
        return self._impl.name

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


@driver_manager.register("ipython")
class IPythonDriver(TerminalDriverProtocol):
    def __init__(self, command: str = "ipython", name: str = "ipython"):
        self._command = command
        self._name = name
        import re
        self._in_pattern = re.compile(r"In \[(\d+)\]:")

        self._is_first = True
        
    @property
    def name(self) -> str:
        return self._name

    @property
    def command(self) -> str:
        return self._command

    @property
    def eol(self) -> str | None:
        return None

    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool:
        # 最終行付近にプロンプト In [x]: がなければ busy とみなす
        lines = [line.strip() for line in snapshot.content.split("\n") if line.strip()]
        if not lines:
            return True
        last_line = lines[-1]
        is_ready = bool(self._in_pattern.match(last_line))
        return not is_ready

    def make_operations(self, input_str: str) -> Sequence[InputOperation]:
        result: list[InputOperation] = []
        def _is_prepared(snapshot: Snapshot) -> bool:
            content = snapshot.content 
            lines = [line.strip("\r ") for line in content.split("\n") if line]
            lines = [line for line in lines if line]
            if not lines:
                return False
            last_line = lines[-1]
            return bool(self._in_pattern.match(last_line))

        if self._is_first:
            # [Weak guess]: It seems a little bit wait is required after the dislay.
            result += [WaitUntilOperation(_is_prepared, timeout=2.0), WaitOperation(0.5)]
            self._is_first = False

        # Empty CRLF is uncecessary....
        body = input_str.replace("\r\n", "\n").replace("\n", "\r").strip("\r")

        result += [
            RawStr("%cpaste -q\n"), #LineStr("%cpaste -q") # This is not good, since `\r` seems to be recognized as the other meaning. 
            WaitOperation(0.5),
            RawStr(body),
            WaitOperation(0.5),
            RawStr("\r--\r"),
        ]
        return result

    def interrupt(self, pid: int, children_pids: list[int]) -> InterruptionCode | None:
        return InterruptionCode(preference="sigint")
