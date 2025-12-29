from typing import Protocol, Sequence
from pathlib import Path
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.core.models import CharacterRange, LineRange


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
        """Return whether the buffer is regarded as ediable and
        can be created in the domain of `pytoy`.
        """
        ...

    def append(self, content: str) -> None: ...

    @property
    def content(self) -> str: ...

    def show(self) -> None: ...

    def hide(self) -> None: ...

    @property
    def range_operator(self) -> "RangeOperatorProtocol":
        ...


class RangeOperatorProtocol(Protocol):
    @property
    def buffer(self) -> PytoyBufferProtocol: ...

    def get_lines(self, line_range: LineRange) -> list[str]: ...

    def get_text(self, character_range: CharacterRange) -> str: ...

    def replace_text(self, character_range: CharacterRange, text: str) -> None: ...

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> None: ...

    def find_first(
        self,
        text: str,
        start_position: CursorPosition | None = None,
        reverse: bool = False,
    ) -> CharacterRange | None:
        """return the first mached selection of `text`."""

    def find_all(self, text: str) -> list[CharacterRange]:
        """return the all matched selections of `text`"""
        ...
