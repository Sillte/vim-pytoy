from __future__ import annotations
from pathlib import Path
from pytoy.infra.core.models.event import Event
from pytoy.ui.pytoy_window.impls.vim.kernel import VimWindowKernel
import vim
from typing import Sequence, assert_never, cast, Literal, Self, TYPE_CHECKING
from pytoy.infra.core.models import CursorPosition, CharacterRange, LineRange
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impls.vim import PytoyBufferVim
from pytoy.ui.pytoy_window.models import ViewportMoveMode, BufferSource, WindowCreationParam
from pytoy.ui.pytoy_window.vim_window_utils import VimWinIDConverter, get_last_selection

from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
    PytoyWindowID,
    StatusLineManagerProtocol,
    WindowEvents
)
from pytoy.ui.status_line import StatusLineManager

if TYPE_CHECKING: 
    from pytoy.contexts.vim import GlobalVimContext


class PytoyWindowVim(PytoyWindowProtocol):
    """
    Implementation of the PytoyWindowProtocol for the Vim editor.
    Provides methods to interact with the Vim UI for Pytoy.
    """
    # NOTE: In neovim, `vim.Window` does not exist.
    def __init__(self, winid: int, *, ctx: GlobalVimContext | None = None):
        from pytoy.contexts.vim import GlobalVimContext
        if ctx is None:
            ctx = GlobalVimContext.get()
        self._kernel = ctx.window_kernel_registry.get(winid)
        self._winid = self._kernel.winid

        
    @classmethod
    def from_vim_window(cls, window: "vim.Window") -> Self:
        return cls(VimWinIDConverter.from_vim_window(window))

    @property
    def winid(self) -> int:
        return self._kernel.winid

    @property
    def buffer(self) -> PytoyBuffer:
        # [TODO]: After refactoring of buffer ended.
        if not (vim_buffer := self._kernel.buffer):
            raise RuntimeError("Already `Window` is deleted.")
        impl = PytoyBufferVim.from_buffer(vim_buffer)
        return PytoyBuffer(impl)
    
    @property
    def window(self) -> "vim.Window | None":
        return self._kernel.window

    @property
    def valid(self) -> bool:
        return self._kernel.valid


    def is_left(self) -> bool:
        """Return whether this is the leftmost window."""
        if not self.window:
            return False

        winid = int(vim.eval(f"win_getid({self.window.number})"))
        info = vim.eval(f"getwininfo({winid})")
        if not info:
            return False
        info = info[0]
        return int(info.get("wincol", 2)) <= 1

    def close(self) -> bool:
        vim_window = self.window
        if not vim_window:
            return True
        if not vim_window.valid:
            return True
        if vim_window == vim.current.window:
            vim.command("close")
        else:
            vim.command(f"{vim_window.number}wincmd c")
        return True

    def focus(self) -> bool:
        vim_window = self.window
        if (not vim_window) or (not vim_window.valid):
            return False
        vim.current.window = vim_window
        return True

    @property
    def on_closed(self) -> Event[PytoyWindowID]:
        return self._kernel.on_closed

    @property
    def status_line_manager(self) ->  StatusLineManagerProtocol:
        return StatusLineManager(self.events)

    @property
    def events(self) -> WindowEvents:
        return self._kernel.events

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PytoyWindowVim):
            return NotImplemented
        return self._kernel == other._kernel

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None:
        provider = PytoyWindowProviderVim()
        provider.retain_unique_window(self, within_tabs=within_tabs, within_windows=within_windows)

    @property
    def cursor(self) -> CursorPosition:
        if not (vim_window := self.window):
            raise RuntimeError(f"Already Window is dead {self.winid}")
        vim_line, col = vim_window.cursor
        # NOTE: "vim.Window.cursor" is a little bit special (line: 1-based, cur: 0-based))
        vim_col = col + 1
        return self._from_vim_coords(vim_line, vim_col)

    def move_cursor(self, cursor: CursorPosition,
                    viewport_mode: ViewportMoveMode = ViewportMoveMode.NONE) -> None:
        vim_line, vim_col =  self._to_vim_coords(cursor)
        if not (vim_window := self.window):
            raise RuntimeError(f"Already Window is dead {self.winid}")
        vim_window.cursor = (vim_line, vim_col)

        winid = self.winid
        match viewport_mode:
            case ViewportMoveMode.NONE:
                pass
            case ViewportMoveMode.CENTER:
                vim.command(f'call win_execute({winid}, "normal! zz")')
            case ViewportMoveMode.TOP:
                vim.command(f'call win_execute({winid}, "normal! zt")')
            case ViewportMoveMode.ENSURE_VISIBLE:
                vim.command(f'call win_execute({winid}, "normal! zv")')
            case _ as unreachable:
                assert_never(unreachable)

    @property
    def selection(self) -> CharacterRange:
        selection = get_last_selection(self.winid)
        if selection:
            return selection
        else:
            return CharacterRange(self.cursor, self.cursor)

    @property
    def selected_line_range(self) -> LineRange:
        return self.selection.as_line_range(cut_first_line=False, cut_last_line=False)

    # VimCoords: (The coordination of VimScript: (line, col): 1-based.)

    def _from_vim_coords(self, vim_line: int, vim_col: int) -> CursorPosition:
        """Solves
        1. 1-base -> 0-base
        2. handling of bytes.
        """
        n_line = max(0, vim_line - 1)
        line_content = self.buffer.lines[n_line]
        line_bytes = line_content.encode('utf-8')
        byte_offset = min(vim_col - 1, len(line_bytes))  # 0-based and to be safe.
        res_col = len(line_bytes[:byte_offset].decode('utf-8', errors='ignore'))
        return CursorPosition(n_line, res_col)

    def _to_vim_coords(self, cursor: CursorPosition) -> tuple[int, int]:
        """
        1. 0-base -> 1-base.
        2. handling of bytes.
        """
        lines = self.buffer.lines
        max_line = len(lines)
        if not max_line:
            return (1, 1)
        vim_line = min(max(0, cursor.line), max_line - 1) + 1
        vim_col = len(lines[vim_line - 1][:cursor.col].encode('utf-8')) + 1
        return (vim_line, vim_col)



class PytoyWindowProviderVim(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        vim_win = vim.current.window
        return PytoyWindowVim(VimWinIDConverter.from_vim_window(vim_win))

    def get_windows(self, only_normal_buffers: bool=True) -> Sequence[PytoyWindowProtocol]:
        windows =  vim.current.tabpage.windows # For consistey with visibleEditors in VSCode.
        if only_normal_buffers:
            return [PytoyWindowVim.from_vim_window(elem) for elem in windows if elem.buffer and PytoyBufferVim(elem.buffer.number).is_normal_type]
        return [PytoyWindowVim.from_vim_window(elem) for elem in windows if elem.buffer]

    def open_window(self,
                    source: str | Path | BufferSource,
                    param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] = "in-place") -> PytoyWindowProtocol:
        source = source if isinstance(source, BufferSource) else BufferSource.from_any(source)
        param = param if isinstance(param, WindowCreationParam) else WindowCreationParam.from_literal(param)

        if param.try_reuse:
            if window := self._get_window_by_bufname(source.name, type=source.type):
                return window

        stored_winid = int(vim.eval("win_getid()"))
        window = self._create_window(source, param)
        if stored_winid > 0:
            vim.command(f"call win_gotoid({stored_winid})")
        return PytoyWindowVim.from_vim_window(window)


    def _create_window(self, source: BufferSource, param: WindowCreationParam) -> "vim.Window":
        target = source.name
        anchor = param.anchor
        is_file = source.type == "file"
        if anchor is None:
            anchor = self.get_current()
        anchor = cast(PytoyWindowVim, anchor)

        if not (anchor_vim_window:= anchor.window):
            print("Anchor Window is already dead.")
            base_winid = 0
        else:
            base_winid = int(vim.eval(f"win_getid({anchor_vim_window.number})"))

        if base_winid > 0:
            vim.command(f"call win_gotoid({base_winid})")

        if param.target == "split":
            split_cmd = "vertical belowright split" if param.split_direction == "vertical" else "belowright split"
            vim.command(split_cmd)

        bufno = int(vim.eval(f'bufnr("{target}")'))

        if bufno <= 0:
            # New buffer.
            vim.command(f"edit {target}")
            window = vim.current.window
            if not is_file:
                window.buffer.options["buftype"] = "nofile"
                window.buffer.options["swapfile"] = False
        else:
            # Switch buffer.
            if vim.current.buffer.number != bufno:
                vim.command(f"buffer {bufno}")
            window = vim.current.window
        return window

    def _get_window_by_bufname(
        self, bufname: str, *, type: Literal["file", "nofile"] = "file"
    ) -> PytoyWindowVim | None:
        """If there exists a visible window displaying a buffer which corresopnds to `bufname`, 
        it returns.

        """
        # [TODO]: This re-use logic is not perfect and based on the observation.
        def _is_equal(buffer: "vim.Buffer", bufname: str):
            if type == "nofile":
                return buffer.name and Path(buffer.name).name == bufname
            elif type == "file":
                return buffer.name and Path(buffer.name).resolve() == Path(bufname).resolve()
            raise RuntimeError("In _get_window_by_buf_name")

        for window in vim.windows:
            winnr = int(vim.eval(f"bufwinnr({window.buffer.number})"))
            if winnr <= 0:
                continue
            if _is_equal(window.buffer, bufname):
                return PytoyWindowVim.from_vim_window(window)
        return None

    def retain_unique_window(self, target_window: PytoyWindowVim, within_tabs: bool = False, within_windows: bool = True) -> None:
        windows = self.get_windows()
        if within_windows:
            for window in windows:
                if window != target_window:
                    window.close()
        if within_tabs:
            target_window.focus()
            vim.command("tabonly")
