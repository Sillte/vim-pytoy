from __future__ import annotations
from pathlib import Path
from pytoy.infra.core.entity import EntityRegistry
from pytoy.ui.pytoy_buffer.impls.vscode.kernel import VSCodeBufferKernel
from pytoy.ui.pytoy_buffer.impls.vscode.kernel import normalize_lf_code
from pytoy.ui.pytoy_buffer.impls.vscode.range_operator import RangeOperatorVSCode
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol, Event, BufferID, BufferEvents
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver, Uri
from pytoy.ui.vscode.document import Document
from pytoy.ui.utils import to_filepath
from typing import Sequence, TYPE_CHECKING, Self

import vim

if TYPE_CHECKING:
    from pytoy.ui.pytoy_window.protocol import PytoyWindowProtocol
    from pytoy.contexts.vscode import GlobalVSCodeContext
    

class PytoyBufferVSCode(PytoyBufferProtocol):
    def __init__(self, bufnr: BufferID, *, ctx: GlobalVSCodeContext | None =None):

        if ctx is None:
            from pytoy.contexts.vscode import GlobalVSCodeContext  # ✅ 実装時のみインポート
            ctx = GlobalVSCodeContext.get()
        kernel_registry: EntityRegistry = ctx.buffer_kernel_registry
        self._kernel: VSCodeBufferKernel = kernel_registry.get(bufnr)

    @property
    def buffer_id(self) -> BufferID:
        return self._kernel.bufnr

    @property
    def kernel(self) -> VSCodeBufferKernel:
        return self._kernel

    @property
    def bufnr(self, ) -> BufferID:
        return self._kernel.bufnr
    
    @property
    def uri(self) -> Uri:
        uri = self._kernel.uri
        if uri is None:
            raise RuntimeError(f"Correspoing URI is not existent, {self.bufnr=}")
        return uri
        
    @property
    def document(self) -> Document:
        return Document(uri=self.uri)
        
    @classmethod
    def from_document(cls, document: Document) -> Self:
        uri = document.uri
        bufnr = BufferURISolver.get_bufnr(uri)
        if bufnr is None:
            raise ValueError(f"Correspoinding buffer is not existent. `{bufnr=}`")
        return cls(bufnr)

    @property
    def on_wiped(self) -> Event[BufferID]:
        return self._kernel.on_end

    @property
    def events(self) -> BufferEvents:
        return self._kernel.events

    @classmethod
    def get_current(cls) -> PytoyBufferProtocol:
        return PytoyBufferVSCode.from_document(Document.get_current())

    @property
    def path(self) -> Path:
        uri = self.uri
        if uri.fsPath:
            elem = uri.fsPath
            elem = elem.replace("\\", "/")  # required to replace.
            return to_filepath(elem)
        else:
            return to_filepath(uri.path)

    @property
    def is_file(self) -> bool:
        """Return True if the buffer corresponds to a file on disk."""
        return self.uri.scheme in {"file", "vscode-remote"}

    @property
    def is_normal_type(self) -> bool:
        """Return whether this buffer is editable/usable by pytoy.

        Treat file-backed buffers and untitled editors as normal.
        """
        try:
            scheme = self.uri.scheme
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
        content = normalize_lf_code(content)
        content = "\n" + content  # correspondence to `vim`.
        self.document.append(content)


    @property
    def content(self) -> str:
        return normalize_lf_code(self.document.content)


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
        return RangeOperatorVSCode(self.kernel)

    def get_windows(self, only_visible: bool = True) -> Sequence["PytoyWindowProtocol"]:
        from pytoy.ui.pytoy_window.impls.vscode import PytoyWindowVSCode
        #editors = [editor for editor in Editor.get_editors(only_visible=only_visible)
        #            if editor.uri == self.document.uri]
        res = vim.eval(f"win_findbuf({self.bufnr})")
        winids = [int(wid) for wid in res] if res else []
        return [PytoyWindowVSCode(winid) for winid in winids]
