from .protocol import ApplicationProtocol
from .utils import force_kill


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

    def interrupt(self, children_pids: list[int]):
        """Interrupt the process.
        """
        for child in children_pids:
            force_kill(child)

