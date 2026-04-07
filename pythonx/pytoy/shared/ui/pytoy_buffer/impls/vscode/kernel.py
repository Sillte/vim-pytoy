from __future__ import annotations
from pytoy.shared.ui.pytoy_buffer.models import BufferEvents, URI
import vim

from typing import TYPE_CHECKING

from pytoy.shared.lib.entity import MortalEntityProtocol
from pytoy.shared.ui.pytoy_buffer.impls.vim.kernel import VimBufferKernel
from pytoy.shared.ui.pytoy_buffer.protocol import Event
from pytoy.shared.ui.vscode.buffer_uri_solver import BufferURISolver, VSCodeUri
from pytoy.shared.ui.vscode.document import Document

if TYPE_CHECKING: 
    from pytoy.contexts.vscode import GlobalVSCodeContext


class VSCodeBufferKernel(MortalEntityProtocol):
    def __init__(self, bufnr: int, *, ctx: GlobalVSCodeContext | None = None):
        from pytoy.contexts.vscode import GlobalVSCodeContext
        if ctx is None:
            ctx = GlobalVSCodeContext.get()
        self._bufnr = bufnr
        self._vim_kernel = VimBufferKernel(bufnr, ctx=ctx.vim_context)
        self.on_wipeout = self._vim_kernel.on_end
        
    @property
    def entity_id(self) -> int:
        return self._bufnr

    @property
    def on_end(self) -> Event[int]:
        return self._vim_kernel.on_end

    @property
    def events(self) -> BufferEvents:
        return self._vim_kernel.events

    @property
    def bufnr(self) -> int:
        return self._vim_kernel.bufnr

    @property
    def bufname(self) -> str | None:
        return self._vim_kernel.bufname

    @property
    def buffer(self) -> "vim.Buffer | None":
        return self._vim_kernel.buffer

    @property
    def uri(self) -> URI:
        vscode_uri = BufferURISolver.get_uri(self.bufnr)
        if vscode_uri is None:
            raise RuntimeError(f"Correspoing URI is not existent, {self.bufnr=}")
        return URI(scheme=vscode_uri.scheme, path=vscode_uri.path, authority=vscode_uri.authority)

    @property
    def vscode_uri(self) -> VSCodeUri | None:
        return BufferURISolver.get_uri(self.bufnr)

    @property
    def document(self) -> Document | None:
        vscode_uri = self.vscode_uri
        return Document(uri=vscode_uri) if vscode_uri else None

    @property
    def content(self) -> str:
        return self._vim_kernel.content

    @property
    def lines(self) -> list[str]:
        return self._vim_kernel.lines


def normalize_lf_code(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
