from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode
from pytoy.ui.pytoy_window.protocol import PytoyWindowProtocol, PytoyWindowProviderProtocol
from pytoy.ui.vscode.editor import Editor

class PytoyWindowVSCode(PytoyWindowProtocol):
    
    def __init__(self, editor: Editor):
        self.editor = editor

    @property
    def buffer(self) -> PytoyBuffer | None:
        impl = PytoyBufferVSCode(self.editor.document)
        return PytoyBuffer(impl)

    @property
    def valid(self) -> bool: 
        return self.editor.valid

    def is_left(self) -> bool:
        return self.editor.viewColumn == 1

class PytoyWindowProviderVSCode(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        return PytoyWindowVSCode(Editor.get_current())

