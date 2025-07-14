from .protocol import ApplicationProtocol
from .utils import find_children, force_kill


class ShellApplication(ApplicationProtocol):
    def __init__(self, command: str, line_suffix: str="\r\n"):
        self._command = command
        self._line_suffix = line_suffix

    @property
    def command(self) -> str:
        return self._command 

    def is_busy(self, pid: int, lastline: str) -> bool:
        _ = lastline
        return bool(find_children(pid))

    def modify(self, input_str: str) -> str: 
        """Modify the command before sending to `terminal`
        """
        return input_str + self._line_suffix

    def interrupt(self, pid: int):
        """Interrupt the process.
        """
        for child in find_children(pid):
            force_kill(child)

