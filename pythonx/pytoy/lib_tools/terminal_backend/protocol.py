"""Terminal, which is used by python.
"""
from typing import Protocol
from queue import Queue

class TerminalBackendProtocol(Protocol):
    def start(self, ) -> None:
        """Start the terminal.
        """

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
        """Stop the child process.
        """

    def terminate(self) -> None:
        """Kill the terminal.
        """
        ...

    @property
    def queue(self) -> Queue:
        """It returns the queue which is used for output. 
        """
        ...

    @property
    def last_line(self) -> str:
        """The current last line backend recognizes.
        """
        ...




class ApplicationProtocol(Protocol):

    @property
    def command(self) -> str:
        """The name of command 
        """
        ...

    def is_busy(self, children_pids: list[int], lastline: str) -> bool | None:
        """Return whether the `terminal` is busy or not. 
        Note that sometimes, the estimation is not perfect. (very difficult to realize 100%).
        If the return is True, it is 100% sure that the process is busy, 
        If the return is False, it cannot guarantee that the process is NOT working.
        (When we have to rely on the lastline, mis-detection cannot be avoided)
        """
        ...

    def modify(self, input_str: str) -> str: 
        """Modify the command before sending to `terminal`
        """
        ...

    def interrupt(self, children_pids: list[int]):
        """Interrupt the process.
        """
        ...


