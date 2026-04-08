from __future__ import annotations
from pathlib import Path
from pytoy.shared.lib.entity import EntityRegistry
from pytoy.shared.lib.event.domain import Event
from pytoy.shared.ui.pytoy_buffer.impls.vscode.kernel import VSCodeBufferKernel
from pytoy.shared.ui.pytoy_buffer.impls.vscode.kernel import normalize_lf_code
from pytoy.shared.ui.pytoy_buffer.impls.vscode.range_operator import RangeOperatorVSCode
from pytoy.shared.ui.pytoy_buffer.models import BufferEvents, BufferQuery, BufferSource
from pytoy.shared.ui.pytoy_buffer.models import URI as PytoyURI
from pytoy.shared.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol, PytoyBufferProviderProtocol, BufferID
from pytoy.shared.ui.vscode.buffer_uri_solver import BufferURISolver, VSCodeUri
from pytoy.shared.ui.vscode.document import Document
from pytoy.shared.ui.utils import to_filepath
from typing import Sequence, TYPE_CHECKING, Self

import vim

if TYPE_CHECKING:
    from pytoy.shared.ui.pytoy_window.protocol import PytoyWindowProtocol
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
    def document(self) -> Document:
        vscode_uri = self._kernel.vscode_uri
        if vscode_uri is None:
            raise RuntimeError(f"Correspoing URI is not existent, {self.bufnr=}")
        return Document(uri=vscode_uri)
        
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
    def uri(self) -> PytoyURI:
        uri = self._kernel.uri
        if uri is None:
            raise RuntimeError(f"Correspoing URI is not existent, {self.bufnr=}")
        return uri

    @property
    def source(self) -> BufferSource:
        vscode_uri = self._kernel.vscode_uri
        if vscode_uri is None:
            raise RuntimeError(f"Correspoing URI is not existent, {self.bufnr=}")
        if self.is_file:
            if vscode_uri.fsPath:
                elem = vscode_uri.fsPath
                elem = elem.replace("\\", "/")  # required to replace.
                path = to_filepath(elem)
            else:
                path = to_filepath(vscode_uri.path)
            return BufferSource.from_path(path)
        else:
            return BufferSource.from_str(vscode_uri.path)
        

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
        for window in self.get_windows(only_visible=True):
            try:
                window.close()
            except Exception:
                pass

    @property
    def range_operator(self) -> RangeOperatorProtocol:
        return RangeOperatorVSCode(self.kernel)

    def get_windows(self, only_visible: bool = True) -> Sequence["PytoyWindowProtocol"]:
        from pytoy.shared.ui.pytoy_window.impls.vscode import PytoyWindowVSCode
        #editors = [editor for editor in Editor.get_editors(only_visible=only_visible)
        #            if editor.uri == self.document.uri]
        res = vim.eval(f"win_findbuf({self.bufnr})")
        winids = [int(wid) for wid in res] if res else []
        return [PytoyWindowVSCode(winid) for winid in winids]


class PytoyBufferProviderVSCode(PytoyBufferProviderProtocol):
    def get_buffers(self, is_normal_type: bool = True) -> Sequence[PytoyBufferVSCode]: 
        buffers = [PytoyBufferVSCode(buffer.number) for buffer in vim.buffers if buffer.valid]
        if is_normal_type:
            buffers = [buffer for buffer in buffers if buffer.is_normal_type]
        return buffers

    def get_current(self) -> PytoyBufferProtocol:
        return PytoyBufferVSCode.from_document(Document.get_current())
    
