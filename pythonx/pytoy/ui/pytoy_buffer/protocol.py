from typing import Protocol
from pathlib import Path


class PytoyBufferProtocol(Protocol):
    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""

    @classmethod
    def get_current(cls) -> "PytoyBufferProtocol":
        ...

    @property
    def valid(self) -> bool:
        """Whether the buffer is alive or not.
        """
        ...

    @property
    def path(self) -> Path | None:
        """Return the file path, if buffer corresponds to `file`.
        If not, it returns None.
        """
        ...


    def append(self, content: str) -> None:
        ...

    @property
    def content(self) -> str:
        ...

    def show(self):
        ...

    def hide(self):
        ...


class RangeSelectorProtocol(Protocol):
    @property
    def buffer(self) -> PytoyBufferProtocol:
        ...

    def get_lines(self, line1: int, line2: int) -> list[str]:
        ...

    def get_range(self, line1: int, pos1:int, line2: int, pos2: int) -> str:  
        ...
