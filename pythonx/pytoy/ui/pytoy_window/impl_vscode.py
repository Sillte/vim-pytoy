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
from pytoy.ui.vscode.document import BufferURISolver, Uri, Api
from pytoy.ui.vscode.editor import Editor
from pytoy.ui.vscode.utils import wait_until_true


class PytoyWindowVSCode(PytoyWindowProtocol):
    def __init__(self, editor: Editor):
        self.editor = editor

    @property
    def buffer(self) -> PytoyBuffer:
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

    def unique(self, within_tab: bool = False) -> None:
        self.editor.unique(within_tab=within_tab)


class PytoyWindowProviderVSCode(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        return PytoyWindowVSCode(Editor.get_current())

    def get_windows(self) -> list[PytoyWindowProtocol]:
        editors = self._get_editors()
        return [PytoyWindowVSCode(elem) for elem in editors]

    def create_window(
        self,
        bufname: str,
        mode: str = "vertical",
        base_window: PytoyWindowProtocol | None = None,
    ) -> PytoyWindowVSCode:
        if window := self._get_window_by_bufname(bufname):
            return window

        current = PytoyWindowProviderVSCode().get_current()

        if base_window is None:
            base_window = current

        base_window.focus()

        api = Api()

        vim.command("noautocmd Vsplit" if mode == "vertical" else "noautocmd Split")
        vim.command(f"Edit {bufname}")
        vim.command("wincmd p")  

        wait_until_true(lambda: _current_uri_check(bufname), timeout=1.0)

        uri = api.eval_with_return(
            "vscode.window.activeTextEditor.document.uri", with_await=False
        )
        uri = Uri(**uri)
        wait_until_true(lambda: BufferURISolver.get_bufnr(uri) != None, timeout=1.0)
        vim.command("Tabonly")
        editor = Editor.get_current()
        result = PytoyWindowVSCode(editor)

        current.focus()
        return result

    def _get_editors(self):
        editors = Editor.get_editors()
        uris = set(BufferURISolver.get_uri_to_bufnr())
        return [elem for elem in editors if elem.uri in uris]

    def _get_window_by_bufname(
        self, bufname: str, *, only_non_file: bool = True
    ) -> PytoyWindowVSCode | None:
        """If there exists a visible window displaying a buffer named `bufname` and that buffer
        is not a file buffer, return the corresponding PytoyWindowVim.
        """
        editors = self._get_editors()
        for editor in editors:
            if editor.document.uri.path != bufname:
                continue
            if only_non_file and PytoyBufferVSCode(editor.document).is_file:
                continue
            return PytoyWindowVSCode(editor)
        return None


def _current_uri_check(name: str) -> bool:
    api = Api()

    uri = api.eval_with_return(
        "vscode.window.activeTextEditor?.document?.uri ?? null", with_await=False
    )
    if uri:
        return Path(Uri(**uri).path).name == name
    return False
