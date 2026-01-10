import vim


from pytoy.infra.core.models import CharacterRange, CursorPosition, LineRange
from pytoy.ui.pytoy_buffer.impls.vim.kernel import VimBufferKernel
from pytoy.ui.pytoy_buffer.impls.vim_buffer_utils import VimBufferRangeHandler
from pytoy.ui.pytoy_buffer.protocol import RangeOperatorProtocol
from pytoy.ui.pytoy_buffer.impls.text_searchers import TextSearcher


from typing import Sequence


class RangeOperatorVim(RangeOperatorProtocol):
    def __init__(self, kernel: VimBufferKernel):
        self._kernel = kernel

    @property
    def kernel(self) -> VimBufferKernel:
        return self._kernel

    @property
    def vim_buffer(self) -> "vim.Buffer":
        vim_buffer =  self._kernel.buffer
        if vim_buffer is None:
            raise RuntimeError(f"Invalid `buffer`, {self._kernel.bufnr}")
        return vim_buffer

    def get_lines(self, line_range: LineRange) -> list[str]:
        """Note that line1 and line2 is 0-based.
        The end is exclusive.
        """
        handler = VimBufferRangeHandler(self.vim_buffer)
        return handler.get_lines(line_range)

    def get_text(self, character_range: CharacterRange) -> str:
        """`line` and `pos` are number acquried by `getpos`."""
        # Note that `start.line` and `end.line` is 0-based.
        # Note that `start.col` and `end.col` is 0-based.
        # Note that `end` of selection is exclusive. 
        handler = VimBufferRangeHandler(self.vim_buffer)
        return handler.get_text(character_range)

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        handler = VimBufferRangeHandler(self.vim_buffer)
        return handler.replace_text(character_range, text)

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange:
        handler = VimBufferRangeHandler(self.vim_buffer)
        return handler.replace_lines(line_range, self.vim_buffer[:])


    def _create_text_searcher(self, target_range: CharacterRange | None = None):
        # TODO: In order to enhance efficiency, please consider `partial` handling of `lines`.
        return TextSearcher.create(self.vim_buffer[:], target_range)

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

    @property
    def entire_character_range(self) -> CharacterRange:
        start = CursorPosition(0, 0)
        end_line = len(self.vim_buffer)
        end_col = 0
        end = CursorPosition(end_line, end_col)
        return CharacterRange(start, end)
