from typing import Protocol, Sequence, TYPE_CHECKING, Hashable
from pathlib import Path
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.core.models import CharacterRange, LineRange
from pytoy.infra.core.models.event import Event

BufferID = Hashable

if TYPE_CHECKING:
    from pytoy.ui.pytoy_window.protocol import PytoyWindowProtocol


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

    @property 
    def lines(self) -> list[str]: ...

    def show(self) -> None: ...

    def hide(self) -> None: ...

    @property
    def range_operator(self) -> "RangeOperatorProtocol":
        ...

    def get_windows(self, only_visible: bool = True) -> Sequence["PytoyWindowProtocol"]:
        """Get windows displaying this buffer.
        Args:
            only_visible: If True, return only visible windows inside the same tab.
                          If False, return all windows backeed recognizes.
        """
        ...
        
    @property
    def on_wiped(self) -> Event[BufferID]:
        ...


class RangeOperatorProtocol(Protocol):
    @property
    def buffer(self) -> PytoyBufferProtocol: ...

    def get_lines(self, line_range: LineRange) -> list[str]: ...

    def get_text(self, character_range: CharacterRange) -> str: ...

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange: ...

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange: ...

    def find_first(
        self,
        text: str,
        target_range: CharacterRange | None = None,
        reverse: bool = False,
    ) -> CharacterRange | None:
        ...

    def find_all(self, text: str, target_range: CharacterRange | None = None) -> list[CharacterRange]:
        """return the all matched selections of `text`"""
        ...

    @property
    def entire_character_range(self) -> CharacterRange:
        ...
