from pathlib import Path
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeSelectorProtocol
from pytoy.ui.vscode.document import Document, BufferURISolver


class PytoyBufferVSCode(PytoyBufferProtocol):
    def __init__(self, document: Document):
        self.document = document

    @classmethod
    def get_current(cls) -> PytoyBufferProtocol:
        return PytoyBufferVSCode(Document.get_current())

    @property
    def path(self) -> Path | None:
        """Return the file path, if buffer corresponds to `file`.
        If not, it returns None.
        """
        scheme = self.document.uri.scheme
        if scheme == "file":
            return Path(self.document.uri.path)
        return None


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


class RangeSelectorVSCode(RangeSelectorProtocol):
    def __init__(self, buffer: PytoyBufferVSCode):
        self._buffer = buffer

    @property
    def buffer(self) -> PytoyBufferVSCode:
        return self._buffer

    def get_lines(self, line1: int, line2: int) -> list[str]:
        bufnr = BufferURISolver.get_bufnr(self._buffer.document.uri)
        import vim  # neovim
        return vim.eval(f"getbufline({bufnr}, {line1}, {line2})")

    def get_range(self, line1: int, pos1:int, line2: int, pos2: int) -> str:  
        """`line` and `pos` are number acquried by `getpos`.
        """
        lines: list[str] = self.get_lines(line1, line2)
        if not lines:
            return ""

        if line1 == line2:
            return lines[0][pos1 - 1:pos2 - 1]

        lines[0] = lines[0][pos1 - 1:]
        lines[-1] = lines[-1][:pos2 - 1]
        return "\n".join(lines)
