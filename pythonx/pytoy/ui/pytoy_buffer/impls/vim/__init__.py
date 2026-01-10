from __future__ import annotations
from pytoy.ui.pytoy_buffer.impls.vim.kernel import VimBufferKernel
from pytoy.ui.pytoy_buffer.impls.vim.range_operator import RangeOperatorVim
import vim
from pathlib import Path
from typing import Sequence, TYPE_CHECKING 

VIM_ERROR = getattr(vim, "error", Exception)

from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol, BufferID, BufferEvents
from pytoy.infra.core.entity import EntityRegistry
from pytoy.infra.events.buffer_events import Event

if TYPE_CHECKING:
    from pytoy.ui.pytoy_window.protocol import PytoyWindowProtocol
    from pytoy.contexts.vim import GlobalVimContext



class PytoyBufferVim(PytoyBufferProtocol):
    def __init__(self, bufnr: int, *,  ctx: GlobalVimContext | None = None) -> None:
        if ctx is None:
            from pytoy.contexts.vim import GlobalVimContext  # ✅ 実装時のみインポート
            ctx = GlobalVimContext.get()
        kernel_registry: EntityRegistry[int, VimBufferKernel] = ctx.buffer_kernel_registry
        self._kernel = kernel_registry.get(bufnr)
        
    @property
    def kernel(self) -> VimBufferKernel:
        return self._kernel
    
    @property
    def buffer_id(self) -> BufferID:
        return self._kernel.bufnr

    @property
    def bufnr(self) -> int:
        return self.kernel.bufnr

    @property
    def buffer(self) -> "vim.Buffer":
        if not self.kernel.buffer:
            raise ValueError("Invalid Buffer")
        return self.kernel.buffer

    @classmethod
    def from_buffer(cls, buffer: "vim.Buffer"):
        return cls(buffer.number)

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""
        content = content.replace("\r\n", "\n")
        self.buffer[:] = content.split("\n")

    @classmethod
    def get_current(cls) -> PytoyBufferProtocol:
        return PytoyBufferVim.from_buffer(vim.current.buffer)

    @property
    def path(self) -> Path:
        return Path(self.buffer.name)

    @property
    def is_file(self) -> bool:
        buftype = vim.eval(f"getbufvar({self.buffer.number}, '&buftype')")
        return buftype == "" and bool(self.buffer.name)

    @property
    def is_normal_type(self) -> bool:
        """Return whether the buffer is regarded as editable by pytoy.

        Treat buffers with non-empty 'buftype' or non-modifiable buffers as
        non-normal.
        """
        try:
            buftype = vim.eval(f"getbufvar({self.buffer.number}, '&buftype')")
            return buftype in {"", "nofile"}
        except VIM_ERROR:
            return False
        except (AttributeError, TypeError):
            return False

    @property
    def valid(self) -> bool:
        if self.kernel.buffer:
            return True
        else:
            return False

    def append(self, content: str) -> None:
        if not content:
            return
        content = content.replace("\r\n", "\n")
        lines = content.split("\n")
        if self._is_empty():
            self.buffer[:] = [lines[0]]
        else:
            self.buffer.append(lines[0])
        for line in lines[1:]:
            self.buffer.append(line)

    @property
    def content(self) -> str:
        return self._kernel.content

    @property
    def lines(self) -> list[str]:
        return self._kernel.lines

    def show(self):
        bufnr = self.buffer.number
        winid = int(vim.eval(f"bufwinid({bufnr})"))
        if winid != -1:
            vim.command(f"call win_gotoid({winid})")
        else:
            vim.command(f"buffer {bufnr}")

    def hide(self):
        nr = int(vim.eval(f"bufwinnr({self.buffer.number})"))
        if 0 <= nr:
            vim.command(f":{nr}close")

    def _is_empty(self) -> bool:
        if len(self.buffer) == 0:
            return True
        if len(self.buffer) == 1 and self.buffer[0] == "":
            return True
        return False

    @property
    def range_operator(self) -> RangeOperatorProtocol:
        return RangeOperatorVim(self.kernel)

    def get_windows(self, only_visible: bool = True) -> Sequence["PytoyWindowProtocol"]:
        from pytoy.ui.pytoy_window.impls.vim import PytoyWindowVim

        bufnr = self.buffer.number
        if only_visible:
            return [
                PytoyWindowVim.from_vim_window(window)
                for window in vim.current.tabpage.windows
                if window.buffer.number == bufnr
            ]
        else:
            windows = []
            for tabpage in vim.tabpages:
                for window in tabpage.windows:
                    if window.buffer.number == bufnr:
                        windows.append(PytoyWindowVim.from_vim_window(window))
            return windows

    @property
    def on_wiped(self) -> Event[BufferID]:
        return self.kernel.on_end

    @property
    def events(self) -> BufferEvents:
        return BufferEvents(on_wiped=self.kernel.on_end)

