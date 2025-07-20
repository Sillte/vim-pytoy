from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol
from pytoy.ui.vscode.document import Document, BufferURISolver


class PytoyBufferVSCode(PytoyBufferProtocol):
    def __init__(self, document: Document):
        self.document = document

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
