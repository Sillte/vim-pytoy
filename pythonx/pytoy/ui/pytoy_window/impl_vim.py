import vim
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impl_vim import PytoyBufferVim

from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)


class PytoyWindowVim(PytoyWindowProtocol):
    """
    Implementation of the PytoyWindowProtocol for the Vim editor.
    Provides methods to interact with the Vim UI for Pytoy.
    """

    def __init__(self, window: vim.Window):
        self.window = window

    @property
    def buffer(self) -> PytoyBuffer | None:
        impl = PytoyBufferVim(self.window.buffer)
        return PytoyBuffer(impl)

    @property
    def valid(self) -> bool:
        return self.window.valid

    def is_left(self) -> bool:
        """Return whether this is the leftmost window."""
        winid = int(vim.eval(f"win_getid({self.window.number})"))
        info = vim.eval(f"getwininfo({winid})")
        if not info:
            return False
        info = info[0]
        return int(info.get("wincol", 2)) <= 1

    def close(self) -> bool:
        if not self.window.valid:
            return True
        try:
            if self.window == vim.current.window:
                vim.command("close")
            else:
                vim.command(f"{self.window.number}wincmd c")
        except Exception as e:
            print(e)
            return False
        else:
            return True


class PytoyWindowProviderVim(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        win = vim.current.window
        return PytoyWindowVim(win)

    def get_windows(self) -> list[PytoyWindowProtocol]:
        return [PytoyWindowVim(elem) for elem in vim.windows]

