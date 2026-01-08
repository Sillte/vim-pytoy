from pytoy.infra.core.models import CharacterRange, CursorPosition, LineRange
from pytoy.ui.pytoy_buffer.impls.vim_buffer_utils import VimBufferRangeHandler
from pytoy.ui.pytoy_buffer.impls.vscode.kernel import VSCodeBufferKernel, Uri, Document, normalize_lf_code
from pytoy.ui.pytoy_buffer.protocol import RangeOperatorProtocol
from pytoy.ui.pytoy_buffer.impls.text_searchers import TextSearcher
from pytoy.ui.vscode.utils import wait_until_true


from typing import Sequence


class RangeOperatorVSCode(RangeOperatorProtocol):
    def __init__(self, kernel: VSCodeBufferKernel):
        self._kernel = kernel

    @property
    def kernel(self) ->  VSCodeBufferKernel:
        return self._kernel

    @property
    def bufnr(self) -> int:
        return self._kernel.bufnr

    @property
    def uri(self) -> Uri:
        uri =  self._kernel.uri
        if uri is None:
            raise ValueError(f"`{uri=}` is a invalid buffer.")
        return uri

    @property
    def document(self) -> Document:
        return Document(uri=self.uri)

    def get_lines(self, line_range: LineRange) -> list[str]:
        # Note that `start.line` and `end.line` is 0-based.
        # Note that `start.col` and `end.col` is 0-based.
        # Note that `line2` is exclusive.
        return VimBufferRangeHandler(self.bufnr).get_lines(line_range)

    def get_text(self, character_range: CharacterRange) -> str:
        """`line` and `pos` are number acquried by `getpos`."""
        # Documentを直接扱った方がよいことが判明したら、変える
        return VimBufferRangeHandler(self.bufnr).get_text(character_range)

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange:
        # NOTE: it is illegal to include `\n` in itemes of `lines`.
        # But, currently, it is not checked.

        #  TODO: Currently, this is used to 
        lr = VimBufferRangeHandler(self.bufnr).replace_lines(line_range, lines)

        def _get_doc_lines(lr: LineRange):
            doc = self.kernel.document
            if not doc:
                return []
            return doc.get_lines(lr.start, lr.end)

        def _is_document_changed():
            doc_lines = _get_doc_lines(lr)
            return lines == doc_lines
        flag = wait_until_true(_is_document_changed, timeout=0.5)
        if not flag:
            doc_lines = _get_doc_lines(lr)
            print("Debug", "Document and Buffer is not equal", lr, flush=True)
            print("text", lines, flush=True)
            print("doc_lines", doc_lines, flush=True)


        return lr

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        # TODO: Documentを直接扱った方がよいことが判明したら、変える
        #start, end = selection.start, selection.end
        #self.buffer.document.replace_range(text,
        #                                   start.line,
        #                                   start.col,
        #                                   end.line,
        #                                   end.col)

        cr = VimBufferRangeHandler(self.bufnr).replace_text(character_range, text)
        # [TODO]: For synchronaization between `Document` and `vim.buffer`.

        def _get_doc_text(cr: CharacterRange):
            start, end = cr.start, cr.end
            doc_text = self.document.get_range(start.line, start.col, end.line, end.col)
            return  normalize_lf_code(doc_text)

        def _is_document_changed():
            doc_text = _get_doc_text(cr)
            return doc_text == text

        flag = wait_until_true(_is_document_changed, timeout=1.0)
        if not flag:
            doc_text = _get_doc_text(cr)
            print("Debug", "Document and Buffer is not equal", cr, flush=True)
            print("text", text, flush=True)
            print("doc_text", doc_text, flush=True)

        return cr

    def _create_text_searcher(self, target_range: CharacterRange | None = None):
        return TextSearcher.create(self._kernel.lines, target_range)

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
        end_line = len(self._kernel.lines)
        if self._kernel.lines:
            end_col = len(self._kernel.lines[-1])
        else:
            end_col = 0
        end = CursorPosition(end_line, end_col)
        return CharacterRange(start, end)