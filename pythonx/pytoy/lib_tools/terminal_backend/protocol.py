"""Terminal, which is used by python.
"""
from typing import Protocol, NewType, Sequence
from queue import Queue


LINE_WAITTIME = NewType("LINE_WAITTIME", float)  # Waitint time used for `input`.

class TerminalBackendProtocol(Protocol):
    def start(
        self,
    ) -> None:
        """Start the terminal."""

    def send(self, input_str: str):
        ...

    @property
    def alive(self) -> bool:
        ...

    @property
    def busy(self) -> bool | None:
        """Whether the somework is performed or not.
        if None, the detection mechanism is not implemented for the concrete class.
        Note that reliability of this function is not high for some concrete
        examples.
        """
        ...

    def interrupt(self) -> None:
        """Stop the child process."""

    def terminate(self) -> None:
        """Kill the terminal."""
        ...

    @property
    def queue(self) -> Queue:
        """It returns the queue which is used for output."""
        ...

    @property
    def last_line(self) -> str:
        """The current last line backend recognizes."""
        ...


class ApplicationProtocol(Protocol):
    @property
    def command(self) -> str:
        """The name of command"""
        ...

    def is_busy(self, children_pids: list[int], lastline: str) -> bool | None:
        """Return whether the `terminal` is busy or not.
        Note that sometimes, the estimation is not perfect. (very difficult to realize perfection).
        If the return is True, it is 100% sure that the process is busy,
        If the return is False, it cannot guarantee that the process is NOT working.
        (When we have to rely on the lastline, mis-detection cannot be avoided.)
        """
        ...

    def make_lines(self, input_str: str) -> Sequence[str | LINE_WAITTIME]:
        """Make the lines which is sent into `pty`.

        * If `\r` / `\n` is added at the end of elements, they are sent as is.  
        * Otherwise, the LF is appended at the end of elements.
        """
        ...

    def interrupt(self, pid: int, children_pids: list[int]):
        """Interrupt the process."""
        ...

    def filter(self, lines: Sequence[str]) -> Sequence[str]:
        """Filter the output of `stdout`.
        """
        ...


DEFAULT_LINES = 1024
DEFAULT_COLUMNS = 1024

class LineBufferProtocol(Protocol):
    """Implement LineBuffer, which is used to capture the output of the virtual
    terminal and convert them to lines.
    """


    @property
    def lines(self) -> int:
        """Return the number of lines
        """
        ...

    @property
    def columns(self) -> int:
        """Return the number of columns
        """
        ...


    def feed(self, chunk: str) -> list[str]:
        """Give the `chunk` info into the buffer and
        return the lines which should be displayed.
        """
        ...

    def flush(self) -> list[str]:
        """Return the displayed lines, using the internal state.
        """
        ...
    
    def reset(self, ):
        """Reset the state.  
        """



