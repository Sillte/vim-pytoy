from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol
from pytoy.ui.vscode.document import Document


class PytoyBufferVSCode(PytoyBufferProtocol):
    def __init__(self, document: Document):
        self.document = document

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""
        if content and content[-1] != "\n":
            content += "\n"
        self.document.content = content

    def append(self, content: str) -> None:
        if not content:
            return
        self.document.append(content)

    @property
    def content(self) -> str:
        return self.document.content

    def focus(self):
        self.document.show()

    def hide(self):
        # [NOTE]: Due to the difference of management of window and `Editor` in vscode
        # this it not implemented.
        pass
