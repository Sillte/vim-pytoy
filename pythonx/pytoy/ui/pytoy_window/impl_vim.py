from typing import Self
from pathlib import Path
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

    # NOTE: In neovim, `vim.Window` does not exist.
    def __init__(self, window: "vim.Window"):
        self.window = window

    @property
    def buffer(self) -> PytoyBuffer:
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

    def focus(self) -> bool:
        if not self.window.valid:
            return False
        vim.current.window = self.window
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PytoyWindowVim):
            return NotImplemented
        return self.window == other.window

    def unique(self, within_tab: bool = False) -> None:
        windows = PytoyWindowProviderVim().get_windows()
        for window in windows:
            if window != self:
                window.close()
        if not within_tab:
            vim.command("tabonly!")


class PytoyWindowProviderVim(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        win = vim.current.window
        return PytoyWindowVim(win)

    def get_windows(self) -> list[PytoyWindowProtocol]:
        return [PytoyWindowVim(elem) for elem in vim.windows]

    def create_window(
        self,
        bufname: str,
        mode: str = "vertical",
        base_window: PytoyWindowProtocol | None = None,
    ) -> PytoyWindowProtocol:
        """Append the specified `buffer` to `base_window` vertically or
        horizontally.

        """
        if window:=self._get_window_by_bufname(bufname):
            return window


        if base_window is None:
            base_window = PytoyWindowVim(vim.current.window)

        if not isinstance(base_window, PytoyWindowVim):
            raise RuntimeError("Invalid base_window", base_window)

        vim_base_window = base_window.window

        storedwin = int(vim.eval(f"win_getid({vim.current.window.number})"))
        curwin = int(vim.eval(f"win_getid({vim_base_window.number})"))

        if 0 < curwin:
            vim.command(f":call win_gotoid({curwin})")

        if mode.startswith("v"):
            split_type = "vertical belowright"
        else:
            split_type = "belowright"

        bufno = int(vim.eval(f'bufnr("{bufname}")'))
        if bufno <= 0:
            # Make a new Window.
            vim.command(f"{split_type} new {bufname}")
            window = vim.current.window
            window.buffer.options["buftype"] = "nofile"
            window.buffer.options["swapfile"] = False
        else:
            opt_switchbuf = vim.options["switchbuf"]
            vim.options["switchbuf"] = "useopen"
            vim.command(f"{split_type} sbuffer {bufname}")
            vim.options["switchbuf"] = opt_switchbuf
            window = vim.current.window

        if 0 < storedwin:
            vim.command(f":call win_gotoid({storedwin})")
        return PytoyWindowVim(window)

    def _get_window_by_bufname(self, bufname: str, *, only_non_file: bool = True) -> PytoyWindowVim | None:
        """If there exists a visible window displaying a buffer named `bufname` and that buffer
        is not a file buffer, return the corresponding PytoyWindowVim.
        """
        for window in vim.windows:
            winnr = int(vim.eval(f"bufwinnr({window.buffer.number})"))
            if winnr <= 0:
                continue
            if window.buffer.name and Path(window.buffer.name).name == bufname:
                buffer = PytoyBuffer(PytoyBufferVim(window.buffer))
                if only_non_file and buffer.is_file:
                    continue
                return PytoyWindowVim(window)
        return None

