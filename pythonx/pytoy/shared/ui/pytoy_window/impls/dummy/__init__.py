from pathlib import Path
from typing import Literal, Sequence

from pytoy.shared.lib.event.domain import Event, EventEmitter
from pytoy.shared.lib.text import CharacterRange, CursorPosition, LineRange
from pytoy.shared.ui.contract.buffer import BufferProtocol
from pytoy.shared.ui.contract.buffer.models import BufferSource
from pytoy.shared.ui.contract.window import (
    PytoyWindowID,
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
    StatusLineManagerProtocol,
)
from pytoy.shared.ui.contract.window.models import ViewportMoveMode, WindowCreationParam
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer.impls.dummy import PytoyBufferDummy
from pytoy.shared.ui.status_line.impl_dummy import StatusLineManagerDummy


class PytoyWindowDummy(PytoyWindowProtocol):
    def __init__(self, winid: PytoyWindowID, buffer: BufferProtocol | None = None):
        self._winid = winid
        self._buffer = buffer or PytoyBufferDummy.get_current()
        self.on_closed_emitter = EventEmitter[PytoyWindowID]()
        self._closed = False
        self._cursor = CursorPosition(0, 0)

    @property
    def buffer(self) -> BufferProtocol:
        return self._buffer

    @property
    def valid(self) -> bool:
        return True

    def is_left(self) -> bool:
        return True

    def close(self) -> bool:
        provider = PytoyWindowProviderDummy()
        provider._windows = [w for w in provider._windows if w != self]
        return True

    def focus(self) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PytoyWindowDummy) and other._winid == self._winid

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None:
        pass

    def deduplicate(self, scope: Literal["buffer"] = "buffer") -> None:
        windows = PytoyWindowProviderDummy().get_windows()
        for window in windows:
            if window != self:
                if window.buffer == self.buffer:
                    window.close()

    @property
    def cursor(self) -> CursorPosition:
        return self._cursor

    def move_cursor(self, cursor: CursorPosition, viewport_mode: ViewportMoveMode = ViewportMoveMode.NONE) -> None:
        self._cursor = cursor

    @property
    def selection(self) -> CharacterRange:
        return self.buffer.range_operator.entire_character_range
        # return CharacterRange(self.cursor, CursorPosition(self._cursor.line, self.cursor.col + 1))

    @property
    def selected_line_range(self) -> LineRange:
        return self.selection.as_line_range()

    @property
    def status_line_manager(self) -> StatusLineManagerProtocol:
        return StatusLineManagerDummy()

    @property
    def on_closed(self) -> Event[PytoyWindowID]:
        return self.on_closed_emitter.event


class PytoyWindowProviderDummy(PytoyWindowProviderProtocol):
    _instance: "PytoyWindowProviderDummy | None" = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._windows: list[PytoyWindowProtocol] = []
        self._initialized = True
        self._counter: int = 0

    def _append_window(self, buffer: BufferProtocol | None = None) -> PytoyWindowProtocol:
        self._windows.append(PytoyWindowDummy(self._counter, buffer=buffer))
        self._counter += 1
        return self._windows[-1]

    def get_current(self) -> PytoyWindowProtocol:
        if not self._windows:
            self._windows.append(PytoyWindowDummy(self._counter))
            self._counter += 1
        return self._windows[0]

    def get_windows(self, only_normal_buffers: bool = True) -> Sequence[PytoyWindowProtocol]:
        if not self._windows:
            self._windows.append(PytoyWindowDummy(self._counter))
            self._counter += 1
        return self._windows

    def open_window(
        self, source: str | Path | BufferSource, param: WindowCreationParam | str = "in-place"
    ) -> PytoyWindowProtocol:
        if not isinstance(source, BufferSource):
            source = BufferSource.from_any(source)
        impl = PytoyBufferDummy(buffer_source=source)
        return self._append_window(buffer=impl)
