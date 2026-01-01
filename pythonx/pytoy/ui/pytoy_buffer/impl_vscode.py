from pathlib import Path
from pytoy.infra.core.models import CursorPosition
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pytoy.ui.vscode.document import Document
from pytoy.ui.utils import to_filepath
from pytoy.infra.core.models import CharacterRange, LineRange
from pytoy.ui.pytoy_buffer.vim_buffer_utils import VimBufferRangeHandler
from typing import Sequence
from pytoy.ui.pytoy_buffer.text_searchers import TextSearcher


class PytoyBufferVSCode(PytoyBufferProtocol):
    def __init__(self, document: Document):
        self.document = document

    @classmethod
    def get_current(cls) -> PytoyBufferProtocol:
        return PytoyBufferVSCode(Document.get_current())

    @property
    def path(self) -> Path:
        if self.document.uri.fsPath:
            elem = self.document.uri.fsPath
            elem = elem.replace("\\", "/")  # required to replace.
            return to_filepath(elem)
        else:
            return to_filepath(self.document.uri.path)

    @property
    def is_file(self) -> bool:
        """Return True if the buffer corresponds to a file on disk."""
        return self.document.uri.scheme in {"file", "vscode-remote"}

    @property
    def is_normal_type(self) -> bool:
        """Return whether this buffer is editable/usable by pytoy.

        Treat file-backed buffers and untitled editors as normal.
        """
        try:
            scheme = self.document.uri.scheme
            return scheme in {"file", "vscode-remote", "untitled"}
        except AttributeError:
            return False

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""
        if content and content[-1] != "\n":
            content += "\n"
        self.document.content = content

    @property
    def valid(self) -> bool:
        # Condition of validity.
        # * `self.document` is recognized at vscode.
        # *  Neovim recoginizes the document.
        bufnr = BufferURISolver.get_bufnr(self.document.uri)
        return bufnr is not None

    def append(self, content: str) -> None:
        if not content:
            return
        content = self._normalize_lf_code(content)
        content = "\n" + content  # correspondence to `vim`.
        self.document.append(content)

    def _normalize_lf_code(self, text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @property
    def content(self) -> str:
        return self._normalize_lf_code(self.document.content)


    @property
    def lines(self) -> list[str]: 
        # TODO: consider the more efficient implemntation.
        # For example, if you can get `bufnr`, 
        # it is possible to get the `vim.buffer[:] directly.
        return self.content.split("\n")

    def show(self):
        self.document.show()

    def hide(self):
        # [NOTE]: Due to the difference of management of window and `Editor` in vscode
        # this it not implemented.
        pass

    @property
    def range_operator(self) -> RangeOperatorProtocol:
        return RangeOperatorVSCode(self)


class RangeOperatorVSCode(RangeOperatorProtocol):
    def __init__(self, buffer: PytoyBufferVSCode):
        self._buffer = buffer

    @property
    def buffer(self) -> PytoyBufferVSCode:
        return self._buffer

    def get_lines(self, line_range: LineRange) -> list[str]:
        # Note that `start.line` and `end.line` is 0-based.
        # Note that `start.col` and `end.col` is 0-based.
        # Note that `line2` is exclusive.
        bufnr = BufferURISolver.get_bufnr(self._buffer.document.uri)
        if bufnr is None:
            return []
        return VimBufferRangeHandler(bufnr).get_lines(line_range)

    def get_text(self, character_range: CharacterRange) -> str:
        """`line` and `pos` are number acquried by `getpos`."""
        # Documentを直接扱った方がよいことが判明したら、変える
        bufnr = BufferURISolver.get_bufnr(self._buffer.document.uri)
        if bufnr is None:
            raise ValueError(f"`{self.buffer.document}` is invalid buffer in neovim")
        return VimBufferRangeHandler(bufnr).get_text(character_range)

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange:
        bufnr = BufferURISolver.get_bufnr(self._buffer.document.uri)
        if bufnr is None:
            raise ValueError(f"`{self.buffer.document}` is invalid buffer in neovim")
        return VimBufferRangeHandler(bufnr).replace_lines(line_range, lines)

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        # TODO: Documentを直接扱った方がよいことが判明したら、変える
        #start, end = selection.start, selection.end
        #self.buffer.document.replace_range(text,
        #                                   start.line,
        #                                   start.col,
        #                                   end.line,
        #                                   end.col)
        bufnr = BufferURISolver.get_bufnr(self._buffer.document.uri)
        if bufnr is None:
            raise ValueError(f"`{self.buffer.document}` is invalid buffer in neovim")
        cr = VimBufferRangeHandler(bufnr).replace_text(character_range, text)
        # [TODO]: For synchronaization between `Document` and `vim.buffer`.
        import vim
        vim.command("sleep 100m")
        return cr

    def _create_text_searcher(self, target_range: CharacterRange | None = None):
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


    @property
    def entire_character_range(self) -> CharacterRange:
        start = CursorPosition(0, 0)
        end_line = len(self.buffer.lines)
        if self.buffer.lines:
            end_col = len(self.buffer.lines[-1])
        else:
            end_col = 0
        end = CursorPosition(end_line, end_col)
        return CharacterRange(start, end)