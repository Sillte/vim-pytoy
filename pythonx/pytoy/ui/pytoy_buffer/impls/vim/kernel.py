from __future__ import annotations

import vim
from typing import TYPE_CHECKING

from pytoy.infra.core.entity import MortalEntityProtocol
from pytoy.infra.core.models.event import Event
from pytoy.infra.events.buffer_events import ScopedBufferEventProvider
from pytoy.ui.pytoy_buffer.protocol import BufferEvents

if TYPE_CHECKING:
    from pytoy.contexts.vim import GlobalVimContext


class VimBufferKernel(MortalEntityProtocol):
    def __init__(self, bufnr: int, *, ctx: GlobalVimContext | None = None) -> None:
        self._bufnr = bufnr
        
        if ctx is None:
            from pytoy.contexts.vim import GlobalVimContext
            ctx = GlobalVimContext.get()
        scoped_buffer_event_provider = ScopedBufferEventProvider.from_ctx(ctx)
        self._wipeout_event = scoped_buffer_event_provider.get_wipeout_event(bufnr)
        self._write_pre_event  = scoped_buffer_event_provider.get_write_pre(bufnr)

        self.on_wipeout = self.on_end

    @property
    def entity_id(self) -> int:
        return self._bufnr

    @property
    def on_end(self) -> Event[int]:
        return self._wipeout_event
    
    @property
    def events(self) -> BufferEvents:
        return BufferEvents(on_wiped=self._wipeout_event, 
                            on_pre_buf=self._write_pre_event)
                            
    @property
    def bufnr(self) -> int:
        return self._bufnr

    @property
    def bufname(self) -> str | None:
        buffer = self.buffer
        return buffer.name if buffer else None


    @property
    def buffer(self) -> "vim.Buffer | None":
        try:
            buf = vim.buffers[self._bufnr]
            return buf if buf.valid else None
        except Exception:
            return None

    @property
    def content(self) -> str:
        buffer = self.buffer
        if buffer:
            return vim.eval("join(getbufline({}, 1, '$'), '\n')".format(buffer.number))
        return ""

    @property
    def lines(self) -> list[str]:
        buffer = self.buffer
        return buffer[:] if buffer else []

