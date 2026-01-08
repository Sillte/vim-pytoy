import vim


from pytoy.infra.core.entity import MortalEntityProtocol
from pytoy.infra.events.buffer_events import ScopedBufferEventProvider
from pytoy.ui.pytoy_buffer.impls.vim.kernel import VimBufferKernel
from pytoy.ui.pytoy_buffer.protocol import Event
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver, Uri
from pytoy.ui.vscode.document import Document


class VSCodeBufferKernel(MortalEntityProtocol):
    def __init__(self, bufnr: int):
        self._bufnr = bufnr
        self._vim_kernel = VimBufferKernel(bufnr)
        self._wipeout_event = ScopedBufferEventProvider.get_wipeout_event(bufnr)
        self.on_wipeout = self.on_end

    @property
    def on_end(self) -> Event[int]:
        return self._vim_kernel.on_end

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
    def uri(self) -> Uri | None:
        return BufferURISolver.get_uri(self.bufnr)

    @property
    def document(self) -> Document | None:
        uri = self.uri
        return Document(uri=uri) if uri else None

    @property
    def content(self) -> str:
        return self._vim_kernel.content

    @property
    def lines(self) -> list[str]:
        return self._vim_kernel.lines



def normalize_lf_code(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
