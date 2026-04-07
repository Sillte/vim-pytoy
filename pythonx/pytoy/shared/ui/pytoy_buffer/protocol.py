from __future__ import annotations
from typing import Protocol, Sequence, TYPE_CHECKING, Hashable
from pathlib import Path
from pytoy.shared.lib.text import CharacterRange, LineRange
from pytoy.shared.lib.event.domain import Event
from pytoy.shared.ui.pytoy_buffer.models import BufferEvents, BufferID, BufferQuery, URI, BufferSource

if TYPE_CHECKING:
    from pytoy.shared.ui.pytoy_window.protocol import PytoyWindowProtocol


class PytoyBufferProtocol(Protocol):
    @property
    def buffer_id(self) -> BufferID: ...

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""

    @classmethod
    def get_current(cls) -> "PytoyBufferProtocol": ...

    @property
    def valid(self) -> bool:
        """Whether the buffer is alive or not."""
        ...


    @property
    def uri(self) -> URI:
        """Return the file path."""
        ...
        
    @property
    def source(self) -> BufferSource:
        """Return the source of buffer."""
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
    def range_operator(self) -> "RangeOperatorProtocol": ...

    def get_windows(self, only_visible: bool = True) -> Sequence["PytoyWindowProtocol"]:
        """Get windows displaying this buffer.
        Args:
            only_visible: If True, return only visible windows inside the same tab.
                          If False, return all windows backeed recognizes.
        """
        ...

    @property
    def on_wiped(self) -> Event[BufferID]:
        """The event of deletion is special."""
        ...

    @property
    def events(self) -> BufferEvents: ...


class PytoyBufferProviderProtocol(Protocol):
    def get_buffers(self, is_normal_type: bool = True) -> Sequence[PytoyBufferProtocol]: ...

    def get_current(self) -> PytoyBufferProtocol: ...
    


class RangeOperatorProtocol(Protocol):
    def get_lines(self, line_range: LineRange) -> list[str]: ...

    def get_text(self, character_range: CharacterRange) -> str: ...

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange: ...

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange: ...

    def find_first(
        self,
        text: str,
        target_range: CharacterRange | None = None,
        reverse: bool = False,
    ) -> CharacterRange | None: ...

    def find_all(self, text: str, target_range: CharacterRange | None = None) -> list[CharacterRange]:
        """return the all matched selections of `text`"""
        ...

    @property
    def entire_character_range(self) -> CharacterRange: ...
