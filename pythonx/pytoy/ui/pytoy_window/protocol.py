from __future__ import annotations
from typing import Protocol, Sequence, Literal, Self, Any
from pathlib import Path

from pytoy.infra.core.models.event import Event
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.infra.core.models import CursorPosition, CharacterRange, LineRange
from pytoy.ui.pytoy_window.models import ViewportMoveMode
from pytoy.ui.pytoy_window.models import BufferSource, WindowCreationParam

PytoyWindowID = Any


class PytoyWindowProtocol(Protocol):
    @property
    def buffer(self) -> PytoyBuffer: ...

    @property
    def valid(self) -> bool:
        """Return whether the window is valid or not"""
        ...

    def is_left(self) -> bool:
        """Return whether this is leftwindow or not."""
        ...

    def close(self) -> bool: ...

    def focus(self) -> bool: ...

    def __eq__(self, other: object) -> bool: ...

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None: ...

    @property
    def cursor(self) -> CursorPosition:
        ...

    def move_cursor(self, cursor: CursorPosition,
                    viewport_mode: ViewportMoveMode = ViewportMoveMode.NONE) -> None:
        ...

    @property
    def selection(self) -> CharacterRange:
        ...

    @property
    def selected_line_range(self) -> LineRange:
        ...

    @property
    def on_closed(self) -> Event[PytoyWindowID]:
        ...


class PytoyWindowProviderProtocol(Protocol):
    def get_current(self) -> PytoyWindowProtocol: ...

    def get_windows(self, only_normal_buffers: bool=True) -> Sequence[PytoyWindowProtocol]:
        ...
        
    def open_window(self,
                    source: str | Path | BufferSource,
                    param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] = "in-place") -> PytoyWindowProtocol:
        ...