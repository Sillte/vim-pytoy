from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Sequence

from pytoy.shared.lib.event.domain import Event
from pytoy.shared.lib.events.action_events import KeyActionEvents
from pytoy.shared.lib.text import CharacterRange, LineRange
from pytoy.shared.ui.contract.buffer.models import URI, BufferEvents, BufferID, BufferQuery, BufferSource

if TYPE_CHECKING:
    from pytoy.shared.ui.contract.window import WindowProtocol


class BufferProtocol(Protocol):
    @property
    def buffer_id(self) -> BufferID: ...

    def init_buffer(self, content: str = "") -> None: ...

    @classmethod
    def get_current(cls) -> "BufferProtocol": ...

    @property
    def valid(self) -> bool: ...

    @property
    def uri(self) -> URI: ...

    @property
    def source(self) -> BufferSource: ...

    @property
    def is_file(self) -> bool: ...

    @property
    def is_normal_type(self) -> bool: ...

    def append(self, content: str) -> None: ...

    @property
    def content(self) -> str: ...

    @property
    def lines(self) -> list[str]: ...

    def show(self) -> None: ...

    def hide(self) -> None: ...

    @property
    def range_operator(self) -> "RangeOperatorProtocol": ...

    def get_windows(self, only_visible: bool = True) -> Sequence["WindowProtocol"]: ...

    @property
    def on_wiped(self) -> Event[BufferID]: ...

    @property
    def events(self) -> BufferEvents: ...

    @property
    def actions(self) -> KeyActionEvents: ...


class BufferProviderProtocol(Protocol):
    def get_buffers(self, is_normal_type: bool = True) -> Sequence[BufferProtocol]: ...

    def get_current(self) -> BufferProtocol: ...


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

    def find_all(self, text: str, target_range: CharacterRange | None = None) -> list[CharacterRange]: ...

    @property
    def entire_character_range(self) -> CharacterRange: ...


PytoyBufferProtocol = BufferProtocol
PytoyBufferProviderProtocol = BufferProviderProtocol
