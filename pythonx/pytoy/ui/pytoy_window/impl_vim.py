from pathlib import Path
import vim
from typing import Sequence, assert_never, cast, Literal
from pytoy.infra.core.models import CursorPosition, CharacterRange, LineRange
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impl_vim import PytoyBufferVim
from pytoy.ui.pytoy_window.models import ViewportMoveMode, BufferSource, WindowCreationParam
from pytoy.ui.pytoy_window.vim_window_utils import get_last_selection

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
        self._winid = int(vim.eval(f"win_getid({window.number})"))

    @property
    def winid(self) -> int:
        return self._winid

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

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None:
        windows = PytoyWindowProviderVim().get_windows()
        if within_windows:
            for window in windows:
                if window != self:
                    window.close()
        if within_tabs:
            self.focus()
            vim.command("tabonly")

    @property
    def cursor(self) -> CursorPosition:
        line, col = self.window.cursor
        return CursorPosition(line - 1, col)

    def move_cursor(self, cursor: CursorPosition,
                    viewport_mode: ViewportMoveMode = ViewportMoveMode.NONE) -> None:
        self.window.cursor = (cursor.line + 1, cursor.col)
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
    def character_range(self) -> CharacterRange:
        selection = get_last_selection(self.winid)
        if selection:
            return selection
        else:
            return CharacterRange(self.cursor, self.cursor)

    @property
    def line_range(self) -> LineRange:
        return self.character_range.as_line_range(cut_first_line=False, cut_last_line=False)

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




class PytoyWindowProviderVim(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        win = vim.current.window
        return PytoyWindowVim(win)

    def get_windows(self, only_normal_buffers: bool=True) -> Sequence[PytoyWindowProtocol]:
        windows =  vim.current.tabpage.windows # For consistey with visibleEditors in VSCode.
        if only_normal_buffers:
            return [PytoyWindowVim(elem) for elem in windows if PytoyBufferVim(elem.buffer).is_normal_type]
        return [PytoyWindowVim(elem) for elem in windows]

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
        return PytoyWindowVim(window)


    def _create_window(self, source: BufferSource, param: WindowCreationParam) -> "vim.Window":
        target = source.name
        anchor = param.anchor
        is_file = source.type == "file"
        if anchor is None:
            anchor = self.get_current()
        anchor = cast(PytoyWindowVim, anchor)


        base_winid = int(vim.eval(f"win_getid({anchor.window.number})"))

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
                return PytoyWindowVim(window)
        return None
