from typing import Protocol


class PytoyBufferProtocol(Protocol):
    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""

    def append(self, content: str) -> None:
        ...

    @property
    def content(self) -> str:
        ...

    def focus(self):
        ...

    def hide(self):
        ...
