from typing import Protocol
from pathlib import Path
from pytoy.ui.pytoy_buffer.models import Selection, CursorPosition


class PytoyBufferProtocol(Protocol):
    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""

    @classmethod
    def get_current(cls) -> "PytoyBufferProtocol": ...

    @property
    def valid(self) -> bool:
        """Whether the buffer is alive or not."""
        ...

    @property
    def path(self) -> Path:
        """Return the file path."""
        ...

    @property
    def is_file(self) -> bool:
        """Return True if the buffer corresponds to a file.
        Return False for scratch buffers, unnamed buffers, etc.
        """
        ...

    @property
    def is_normal_type(self) -> bool:
        """Return whether the buffer is regarded as ediable and can be created in the  domain of `pytoy`."""
        ...

    def append(self, content: str) -> None: ...

    @property
    def content(self) -> str: ...

    def show(self) -> None: ...

    def hide(self) -> None: ... 



class RangeSelectorProtocol(Protocol):
    @property
    def buffer(self) -> PytoyBufferProtocol: ...

    def get_lines(self, line1: int, line2: int) -> list[str]: ...

    def get_range(self, selection: Selection) -> str: ...

    def replace_range(self, selection: Selection, text: str) -> None:
        ...
