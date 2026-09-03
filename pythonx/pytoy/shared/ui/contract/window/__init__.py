from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, Self, Sequence

from pytoy.shared.lib.event.domain import Event
from pytoy.shared.lib.events.window_events import ScopedWindowEventProvider
from pytoy.shared.lib.text import CharacterRange, CursorPosition, LineRange
from pytoy.shared.ui.contract.buffer.models import BufferSource
from pytoy.shared.ui.contract.status_line import StatusLineManagerProtocol
from pytoy.shared.ui.contract.window.models import ViewportMoveMode, WindowCreationParam

if TYPE_CHECKING:
    from pytoy.contexts.vim import GlobalVimContext
    from pytoy.shared.ui.contract.buffer import BufferProtocol

WindowID = Any


class WindowProtocol(Protocol):
    @property
    def buffer(self) -> "BufferProtocol": ...

    @property
    def valid(self) -> bool: ...

    def is_left(self) -> bool: ...

    def close(self) -> bool: ...

    def focus(self) -> bool: ...

    def __eq__(self, other: object) -> bool: ...

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None: ...

    def deduplicate(self, scope: Literal["buffer"] = "buffer") -> None: ...

    @property
    def cursor(self) -> CursorPosition: ...

    def move_cursor(self, cursor: CursorPosition, viewport_mode: ViewportMoveMode = ViewportMoveMode.NONE) -> None: ...

    @property
    def selection(self) -> CharacterRange: ...

    @property
    def selected_line_range(self) -> LineRange: ...

    @property
    def status_line_manager(self) -> StatusLineManagerProtocol: ...

    @property
    def on_closed(self) -> Event[WindowID]: ...


class WindowProviderProtocol(Protocol):
    def get_current(self) -> WindowProtocol: ...

    def get_windows(self, only_normal_buffers: bool = True) -> Sequence[WindowProtocol]: ...

    def open_window(
        self,
        source: str | Path | BufferSource,
        param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] = "in-place",
    ) -> WindowProtocol: ...


@dataclass
class WindowEvents:
    entity_id: WindowID
    on_closed: Event[WindowID]

    @classmethod
    def from_winid(cls, winid: WindowID, *, ctx: GlobalVimContext | None = None) -> Self:
        from pytoy.contexts.vim import GlobalVimContext

        if ctx is None:
            ctx = GlobalVimContext.get()
        provider = ScopedWindowEventProvider.from_ctx(ctx=ctx)
        return cls(entity_id=winid, on_closed=provider.get_winclosed_event(winid))


PytoyWindowID = WindowID
PytoyWindowProtocol = WindowProtocol
PytoyWindowProviderProtocol = WindowProviderProtocol
