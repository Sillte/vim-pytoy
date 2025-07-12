# **Specification**
# * Editor: Editor of VSCode.
# * Editor of PytoyWindow: the buffers of windows is managed in neovim.


from pathlib import Path
import vim  # (vscode-neovim extention)
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode
from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.ui.vscode.document import BufferURISolver, Uri, Api, Document
from pytoy.ui.vscode.editor import Editor
from pytoy.ui.vscode.utils import wait_until_true
from pytoy.ui.vscode.focus_controller import set_active_viewcolumn


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

    def focus(self) -> bool:
        self.editor.focus()
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PytoyWindowVSCode):
            return NotImplemented
        return self.editor == other.editor

    def unique(self, within_tab: bool=False) -> None:
        self.editor.unique(within_tab=within_tab)


class PytoyWindowProviderVSCode(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        return PytoyWindowVSCode(Editor.get_current())

    def get_windows(self) -> list[PytoyWindowProtocol]:
        editors = Editor.get_editors()
        uris = set(BufferURISolver.get_uri_to_bufnr())
        editors = [elem for elem in editors if elem.uri in uris]
        return [PytoyWindowVSCode(elem) for elem in editors]

    def create_window(
        self,
        bufname: str,
        mode: str = "vertical",
        base_window: PytoyWindowProtocol | None = None,
    ) -> PytoyWindowProtocol:

        current = PytoyWindowProviderVSCode().get_current()

        if base_window is None:
            base_window = current

        base_window.focus()

        api = Api()
        if mode == "vertical":
            vim.command("Vsplit")
        else:
            vim.command("Split")

        vim.command(f"Edit {bufname}")

        wait_until_true(lambda: _current_uri_check(bufname), timeout=0.3)

        uri = api.eval_with_return(
          "vscode.window.activeTextEditor.document.uri", with_await=False
        )
        uri = Uri(**uri)
        wait_until_true(lambda:  BufferURISolver.get_bufnr(uri) != None, timeout=0.3)
        vim.command("Tabonly")
        editor = Editor.get_current()
        result = PytoyWindowVSCode(editor)

        current.focus()
        return result
        

def _current_uri_check(name: str) -> bool:
    api = Api()
    
    uri = api.eval_with_return(
        "vscode.window.activeTextEditor?.document?.uri ?? null", with_await=False
    )
    if uri:
        return Path(Uri(**uri).path).name == name
    return False
  
