from pytoy.ui.pytoy_window.protocol import WindowEvents
import vim
from pytoy.infra.core.entity import MortalEntityProtocol
from pytoy.infra.core.models.event import Event
from pytoy.ui.pytoy_window.protocol import PytoyWindowID


from pytoy.ui.pytoy_window.vim_window_utils import VimWinIDConverter


class VimWindowKernel(MortalEntityProtocol):
    def __init__(self, winid: int):
        self._winid = winid
        # Value Object.
        self._window_events = WindowEvents.from_winid(self._winid)

    @property
    def on_end(self) -> Event[PytoyWindowID]:
        return self.on_closed

    @property
    def entity_id(self) -> PytoyWindowID:
        return self._winid

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VimWindowKernel):
            return False
        return other.winid == self.winid


    @property
    def winid(self) -> int:
        return self._winid

    @property
    def window(self) -> "vim.Window | None":
        return VimWinIDConverter.to_vim_window(self._winid)

    @property
    def buffer(self) -> "vim.Buffer | None":
        if (vim_window:= self.window) is None:
            raise RuntimeError("Already `Window` is deleted.")
        return vim_window.buffer

    @property
    def valid(self) -> bool:
        vim_window = self.window
        if vim_window:
            return bool(vim_window.valid)
        return False


    @property
    def on_closed(self) -> Event[PytoyWindowID]:
        return self._window_events.on_closed