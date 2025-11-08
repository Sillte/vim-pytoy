import re
import time
from typing import Sequence
from pytoy.lib_tools.terminal_backend.application import (
    AppManager,
    ApplicationProtocol,
    LINE_WAITTIME,
)
from pytoy.lib_tools.terminal_backend.utils import send_ctrl_c


@AppManager.register(name="ipython")
class IPythonApplication(ApplicationProtocol):
    def __init__(
        self,
    ):
        self._in_pattern = re.compile(r"^In \[(\d+)\]:")
        self._is_prepared = False

    @property
    def command(self) -> str:
        return "ipython"

    def is_busy(self, children_pids: list[int], lastline: str) -> bool | None:
        """Return whether the `terminal` is busy or not.
        Note that sometimes, the estimation is not perfect. (very difficult to realize perfection).
        If the return is True, it is 100% sure that the process is busy,
        If the return is False, it cannot guarantee that the process is NOT working.
        (When we have to rely on the lastline, mis-detection cannot be avoided.)
        """
        return bool(self._in_pattern.match(lastline))

    def make_lines(self, input_str: str) -> Sequence[str | LINE_WAITTIME]:
        """Make the lines which is sent into `pty`.

        * If `\r` / `\n` is added at the end of elements, they are sent as is.
        * Otherwise, the LF is appended at the end of elements.
        """

        self._is_wait_initialization()
        result = []
        result += ["%cpaste -q\n", LINE_WAITTIME(0.3)]
        input_str = input_str.replace("\r\n", "\n")
        input_str = input_str.replace("\n", "\r")
        result.append(input_str)
        result.append(LINE_WAITTIME(0.1))
        result.append("--\r\n")
        result.append(LINE_WAITTIME(0.1))
        result.append("\r\n")
        return result

    def interrupt(self, pid: int, children_pids: list[int]):
        """Interrupt the process."""
        _ = children_pids
        send_ctrl_c(pid)

    def _is_wait_initialization(self, timeout: float = 3.0):
        now = time.time()
        while time.time() - now < timeout and (self._is_prepared is False):
            time.sleep(0.05)

    def filter(self, lines: Sequence[str]) -> Sequence[str]:
        if not self._is_prepared:
            for line in lines:
                if line.startswith("In [1]:"):
                    self._is_prepared = True
        return lines
