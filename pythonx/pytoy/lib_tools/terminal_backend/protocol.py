"""Terminal, which is used by python.
"""
from typing import Protocol
from queue import Queue

class TerminalBackendProtocol(Protocol):
    def start(self, ) -> None:
        """Start the terminal.
        """

    def send(self, cmd: str):
        ...

    @property
    def alive(self) -> bool: 
        ...

    @property
    def busy(self) -> bool: 
        """Whether the somework is performed or not.
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

