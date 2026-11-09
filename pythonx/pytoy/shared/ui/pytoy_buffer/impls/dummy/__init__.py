from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Sequence
from unittest import mock

from pytoy.shared.lib.entity import EntityRegistry
from pytoy.shared.lib.event.domain import Event, EventEmitter
from pytoy.shared.lib.events.action_events import KeyActionEvents
from pytoy.shared.lib.text import CharacterRange, CursorPosition, LineRange
from pytoy.shared.ui.contract.buffer import (
    URI,
    BufferEvents,
    BufferID,
    BufferMetadata,
    BufferQuery,
    BufferSource,
    RangeOperatorProtocol,
)
from pytoy.shared.ui.contract.buffer import (
    BufferProtocol as PytoyBufferProtocol,
)
from pytoy.shared.ui.contract.buffer import (
    BufferProviderProtocol as PytoyBufferProviderProtocol,
)
from pytoy.shared.ui.pytoy_buffer.content_utils import (
    normalize_buffer_content,
    prepare_append_lines,
    split_buffer_content,
)

if TYPE_CHECKING:
    from pytoy.shared.ui.contract.window import WindowProtocol as PytoyWindowProtocol


class RangeOperatorDummy(RangeOperatorProtocol):
    def __init__(self, lines: list[str]):
        self._lines = lines

    def get_lines(self, line_range: LineRange) -> list[str]:
        return self._lines[line_range.start : line_range.end]

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange:
        self._lines[line_range.start : line_range.end] = lines
        if not self._lines:
            self._lines.append("")
        return LineRange(line_range.start, line_range.start + len(lines))

    def get_text(self, character_range: CharacterRange) -> str:
        full_text = "\n".join(self._lines)
        start = self._cursor_to_offset(character_range.start)
        end = self._cursor_to_offset(character_range.end)
        return full_text[start:end]

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        text = normalize_buffer_content(text)
        full_text = "\n".join(self._lines)
        start = self._cursor_to_offset(character_range.start)
        end = self._cursor_to_offset(character_range.end)
        new_text = full_text[:start] + text + full_text[end:]
        self._lines[:] = split_buffer_content(new_text)
        end_cursor = self._offset_to_cursor(start + len(text))
        return CharacterRange(character_range.start, end_cursor)

    def find_first(
        self, text: str, target_range: CharacterRange | None = None, reverse: bool = False
    ) -> CharacterRange | None:
        haystack = self.get_text(target_range) if target_range else "\n".join(self._lines)
        index = haystack.rfind(text) if reverse else haystack.find(text)
        if index == -1:
            return None
        start_cursor = self._offset_to_cursor(index)
        end_cursor = self._offset_to_cursor(index + len(text))
        return CharacterRange(start_cursor, end_cursor)

    def find_all(self, text: str, target_range: CharacterRange | None = None) -> list[CharacterRange]:
        haystack = self.get_text(target_range) if target_range else "\n".join(self._lines)
        results = []
        offset = 0
        while True:
            index = haystack.find(text, offset)
            if index == -1:
                break
            start_cursor = self._offset_to_cursor(index)
            end_cursor = self._offset_to_cursor(index + len(text))
            results.append(CharacterRange(start_cursor, end_cursor))
            offset = index + len(text)
        return results

    @property
    def entire_character_range(self) -> CharacterRange:
        if not self._lines:
            return CharacterRange(CursorPosition(0, 0), CursorPosition(0, 0))
        last_line_idx = len(self._lines) - 1
        last_col_idx = len(self._lines[-1])
        return CharacterRange(CursorPosition(0, 0), CursorPosition(last_line_idx, last_col_idx))

    def _cursor_to_offset(self, pos: CursorPosition) -> int:
        return sum(len(self._lines[i]) + 1 for i in range(pos.line)) + pos.col

    def _offset_to_cursor(self, offset: int) -> CursorPosition:
        total = 0
        for i, line in enumerate(self._lines):
            if total + len(line) >= offset:
                return CursorPosition(i, offset - total)
            total += len(line) + 1
        return CursorPosition(len(self._lines) - 1, len(self._lines[-1]))


class PytoyBufferDummy(PytoyBufferProtocol):
    def __init__(self, buffer_source: BufferSource):
        self._lines: list[str] = [""]
        self._buffer_source = buffer_source
        self._buffer_id = id(buffer_source)
        self.on_wiped_emitter = EventEmitter[BufferID]()
        self.on_pre_buf_emitter = EventEmitter[BufferID]()
        self._actions = KeyActionEvents(self._buffer_id)
        self._events = BufferEvents(on_wiped=self.on_wiped_emitter.event, on_pre_buf=self.on_pre_buf_emitter.event)
        self._range_operator = RangeOperatorDummy(self._lines)
        self._is_file = bool(buffer_source.type == "file")
        self._metadata = BufferMetadata()

    @classmethod
    def get_current(cls) -> PytoyBufferDummy:
        return PytoyBufferProviderDummy().get_current()

    @property
    def range_operator(self) -> RangeOperatorProtocol:
        return self._range_operator

    @property
    def events(self) -> BufferEvents:
        return self._events

    @property
    def actions(self) -> KeyActionEvents:
        return self._actions

    @property
    def on_wiped(self) -> Event[BufferID]:
        return self.on_wiped_emitter.event

    @property
    def buffer_id(self) -> BufferID:
        return self._buffer_id

    def init_buffer(self, content: str = ""):
        self._lines[:] = split_buffer_content(content)

    @property
    def uri(self) -> URI:
        return URI(scheme=self._buffer_source.type, path=self._buffer_source.name)

    @property
    def source(self) -> BufferSource:
        return self._buffer_source

    @property
    def is_file(self) -> bool:
        return self._is_file

    @property
    def valid(self) -> bool:
        return True

    @property
    def content(self) -> str:
        return "\n".join(self._lines)

    @property
    def lines(self) -> list[str]:
        return self._lines

    def append(self, content: str) -> None:
        append = prepare_append_lines(
            self._lines[-1],
            content,
            is_empty=len(self._lines) == 1 and not self._lines[0],
        )
        if append is None:
            return
        replace_last_line, lines = append
        if replace_last_line:
            self._lines[-1] = lines[0]
            lines = lines[1:]
        self._lines.extend(lines)

    @property
    def is_normal_type(self) -> bool:
        return True

    @property
    def metadata(self) -> BufferMetadata:
        return self._metadata

    def get_windows(self, only_visible: bool = True) -> Sequence["PytoyWindowProtocol"]:
        # TODO: this is temporary.
        from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
        from pytoy.shared.ui.pytoy_window.impls.dummy import PytoyWindowDummy

        return [PytoyWindowDummy(winid=id(self), buffer=self)]


class PytoyBufferProviderDummy(PytoyBufferProviderProtocol):
    buffers: ClassVar[dict[BufferID, PytoyBufferDummy]] = {}

    def close_buffers(self, buffer_ids: Sequence[BufferID]) -> None:
        target_ids = set(buffer_ids)
        buffers = [buffer for buffer in self.get_buffers(is_normal_type=False) if buffer.buffer_id in target_ids]
        for buffer in buffers:
            if buffer.is_file:
                continue
            buffer.init_buffer("")

        from pytoy.shared.ui.pytoy_window.impls.dummy import PytoyWindowProviderDummy

        for window in list(PytoyWindowProviderDummy().get_windows(only_normal_buffers=False)):
            if window.buffer.buffer_id in target_ids and not window.buffer.is_file:
                window.close()

    @classmethod
    def create_buffer(cls, buffer_source: BufferSource | None = None) -> PytoyBufferDummy:
        import uuid

        buffer_source = buffer_source or BufferSource(name=str(uuid.uuid4()), type="nofile")
        buffer_impl = PytoyBufferDummy(buffer_source)
        cls.buffers[buffer_impl.buffer_id] = buffer_impl
        return cls.buffers[buffer_impl.buffer_id]

    def get_buffers(self, is_normal_type: bool = True) -> Sequence[PytoyBufferProtocol]:
        items = list(self.buffers.values())
        if is_normal_type:
            items = [item for item in items if item.is_normal_type]
        return items

    def get_current(self) -> PytoyBufferDummy:
        if self.buffers:
            return list(self.buffers.values())[0]
        else:
            return self.create_buffer()
