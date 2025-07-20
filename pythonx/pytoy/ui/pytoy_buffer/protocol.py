from typing import Protocol


class PytoyBufferProtocol(Protocol):
    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""

    @property
    def valid(self) -> bool:
        """Whether the buffer is alive or not.
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
