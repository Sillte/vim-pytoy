from pathlib import Path
from pytoy.infra.core.models import CursorPosition
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pytoy.ui.vscode.document import Document
from pytoy.ui.utils import to_filepath
from pytoy.infra.core.models import CharacterRange, LineRange
from pytoy.ui.pytoy_buffer.vim_buffer_utils import VimBufferRangeHandler
from typing import Sequence


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
        content = "\n" + content  # correspondence to `vim`.
        self.document.append(content)

    @property
    def content(self) -> str:
        return self.document.content

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

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> None:
        bufnr = BufferURISolver.get_bufnr(self._buffer.document.uri)
        if bufnr is None:
            raise ValueError(f"`{self.buffer.document}` is invalid buffer in neovim")
        return VimBufferRangeHandler(bufnr).replace_lines(line_range, lines)

    def replace_text(self, character_range: CharacterRange, text: str) -> None:
        # TODO: Documentを直接扱った方がよいことが判明したら、変える
        # その場合、この部分の引数も`Seleciton`に リファクタしたほうがいいね。
        #start, end = selection.start, selection.end
        #self.buffer.document.replace_range(text,
        #                                   start.line,
        #                                   start.col,
        #                                   end.line,
        #                                   end.col)
        bufnr = BufferURISolver.get_bufnr(self._buffer.document.uri)
        if bufnr is None:
            raise ValueError(f"`{self.buffer.document}` is invalid buffer in neovim")
        return VimBufferRangeHandler(bufnr).replace_text(character_range, text)

    def find_first(
        self,
        text: str,
        start_position: CursorPosition | None = None,
        reverse: bool = False,
    ) -> CharacterRange | None:
        """return the first mached selection of `text`."""
        # TODO: Implement this.
        return None

    def find_all(self, text: str) -> list[CharacterRange]:
        """return the all matched selections of `text`"""
        # TODO: Implement this.
        return []

