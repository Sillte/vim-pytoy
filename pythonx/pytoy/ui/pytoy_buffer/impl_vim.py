from pytoy.infra.core.models import CursorPosition
import vim
from pathlib import Path
from pytoy.infra.core.models import CharacterRange
from typing import Sequence 


VIM_ERROR = getattr(vim, "error", Exception)

from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol
from pytoy.infra.core.models import CharacterRange, LineRange
from pytoy.ui.pytoy_buffer.vim_buffer_utils import VimBufferRangeHandler
from pytoy.ui.pytoy_buffer.text_searchers import TextSearcher


class PytoyBufferVim(PytoyBufferProtocol):
    def __init__(self, buffer: "vim.Buffer"):
        self.buffer = buffer

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""
        content = content.replace("\r\n", "\n")
        self.buffer[:] = content.split("\n")

    @classmethod
    def get_current(cls) -> PytoyBufferProtocol:
        return PytoyBufferVim(vim.current.buffer)

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
        return self.buffer.valid

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
        return vim.eval("join(getbufline({}, 1, '$'), '\n')".format(self.buffer.number))

    @property
    def lines(self) -> list[str]:
        return self.buffer[:]

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
        return RangeOperatorVim(self)


class RangeOperatorVim(RangeOperatorProtocol):
    def __init__(self, buffer: PytoyBufferVim):
        self._buffer = buffer

    @property
    def buffer(self) -> PytoyBufferVim:
        return self._buffer

    def get_lines(self, line_range: LineRange) -> list[str]:
        """Note that line1 and line2 is 0-based.
        The end is exclusive.
        """
        handler = VimBufferRangeHandler(self.buffer.buffer)
        return handler.get_lines(line_range)

    def get_text(self, character_range: CharacterRange) -> str:
        """`line` and `pos` are number acquried by `getpos`."""
        # Note that `start.line` and `end.line` is 0-based.
        # Note that `start.col` and `end.col` is 0-based.
        # Note that `end` of selection is exclusive. 
        handler = VimBufferRangeHandler(self.buffer.buffer)
        return handler.get_text(character_range)

    def replace_text(self, character_range: CharacterRange, text: str) -> None:
        handler = VimBufferRangeHandler(self.buffer.buffer)
        return handler.replace_text(character_range, text)

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> None:
        handler = VimBufferRangeHandler(self.buffer.buffer)
        return handler.replace_lines(line_range, lines)


    def _create_text_searcher(self, target_range: CharacterRange | None = None):
        # TODO: In order to enhance efficiency, please consider `partial` handling of `lines`.
        return TextSearcher.create(self.buffer.lines, target_range)

    def find_first(
        self,
        text: str,
        target_range: CharacterRange | None = None,
        reverse: bool = False,
    ) -> CharacterRange | None:
        """return the first mached selection of `text`."""
        searcher = self._create_text_searcher(target_range=target_range)
        return searcher.find_first(text, reverse=reverse)

    def find_all(self, text: str, target_range: CharacterRange | None = None) -> list[CharacterRange]:
        """return the all matched selections of `text`"""
        searcher = self._create_text_searcher(target_range=target_range)
        return searcher.find_all(text)

