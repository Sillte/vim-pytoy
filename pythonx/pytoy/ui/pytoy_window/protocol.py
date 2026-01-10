from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Sequence, Literal, Self, Any, TYPE_CHECKING
from pathlib import Path

from pytoy.infra.core.models.event import Event
from pytoy.infra.events.window_events import ScopedWindowEventProvider
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.infra.core.models import CursorPosition, CharacterRange, LineRange
from pytoy.ui.pytoy_window.models import ViewportMoveMode
from pytoy.ui.pytoy_window.models import BufferSource, WindowCreationParam
from pytoy.ui.status_line.protocol import StatusLineManagerProtocol, StatusLineItem

if TYPE_CHECKING: 
    from pytoy.contexts.vim import GlobalVimContext

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
    def status_line_manager(self) -> StatusLineManagerProtocol:
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

@dataclass
class WindowEvents:
    entity_id: PytoyWindowID
    on_closed: Event[PytoyWindowID]

    @classmethod
    def from_winid(cls, winid: PytoyWindowID, *, ctx: GlobalVimContext | None = None) -> Self:
        from pytoy.contexts.vim import GlobalVimContext
        if ctx is None:
            ctx = GlobalVimContext.get()
        provider = ScopedWindowEventProvider.from_ctx(ctx=ctx)
        return cls(entity_id = winid,
            on_closed = provider.get_winclosed_event(winid)
            )