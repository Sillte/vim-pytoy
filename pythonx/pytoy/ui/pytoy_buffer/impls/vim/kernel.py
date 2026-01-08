import vim

from pytoy.infra.core.entity import MortalEntityProtocol
from pytoy.infra.core.models.event import Event
from pytoy.infra.events.buffer_events import ScopedBufferEventProvider


class VimBufferKernel(MortalEntityProtocol):
    def __init__(self, bufnr: int):
        self._bufnr = bufnr
        self._wipeout_event = ScopedBufferEventProvider.get_wipeout_event(bufnr)
        self.on_wipeout = self.on_end

    @property
    def entity_id(self) -> int:
        return self._bufnr

    @property
    def on_end(self) -> Event[int]:
        return self._wipeout_event

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

