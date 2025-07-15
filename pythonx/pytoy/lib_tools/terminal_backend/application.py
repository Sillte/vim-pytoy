from .protocol import ApplicationProtocol
from .utils import force_kill, send_ctrl_c


class ShellApplication(ApplicationProtocol):
    def __init__(self, command: str, line_suffix: str="\r\n"):
        self._command = command
        self._line_suffix = line_suffix

    @property
    def command(self) -> str:
        return self._command 

    def is_busy(self, children_pids: list[int], lastline: str) -> bool:
        _ = lastline
        return bool(children_pids)

    def modify(self, input_str: str) -> str: 
        """Modify the command before sending to `terminal`
        """
        return input_str + self._line_suffix

    def interrupt(self, pid: int, children_pids: list[int]):
        _ = children_pids
        """Interrupt the process.
        """
        _ = pid
        for child in children_pids:
            force_kill(child)


class InteractiveApplication(ApplicationProtocol):
    def __init__(self, command: str, line_suffix: str="\r\n"):
        self._command = command
        self._line_suffix = line_suffix

    @property
    def command(self) -> str:
        return self._command 

    def is_busy(self, children_pids: list[int], lastline: str):
        return None


    def modify(self, input_str: str) -> str: 
        """Modify the command before sending to `terminal`
        """
        return input_str + self._line_suffix

    def interrupt(self, pid: int,  children_pids: list[int]):
        """Interrupt the process.
        """
        send_ctrl_c(pid)
