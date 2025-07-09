# **Specification**
# * Editor: Editor of VSCode.
# * Editor of PytoyWindow: the buffers of windows is managed in neovim.


from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode
from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.ui.vscode.api import Api
from pytoy.ui.vscode.document import BufferURISolver
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

    def close(self) -> bool:
        return self.editor.close()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PytoyWindowVSCode):
            return NotImplemented
        return self.editor == other.editor

    def isolate(self, tab_scope: bool=False) -> None:
        self.editor.focus()
        api = Api()
        api.call("workbench.action.closeEditorsInOtherGroups")
        if tab_scope:
            api.call("workbench.action.closeOtherEditors")


class PytoyWindowProviderVSCode(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        return PytoyWindowVSCode(Editor.get_current())

    def get_windows(self) -> list[PytoyWindowProtocol]:
        editors = Editor.get_editors()
        uris = set(BufferURISolver.get_uri_to_bufnr())
        editors = [elem for elem in editors if elem.uri in uris]
        return [PytoyWindowVSCode(elem) for elem in editors]
