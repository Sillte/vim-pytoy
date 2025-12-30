# **Specification**
# * Editor: Editor of VSCode.
# * Editor of PytoyWindow: the buffers of windows is managed in neovim.


from pathlib import Path
from pytoy.infra.core.models import CursorPosition
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pytoy.ui.vscode.uri import Uri
import vim  # (vscode-neovim extention)
from typing import Sequence
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode
from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.ui.vscode.document import Api, Document
from pytoy.ui.vscode.editor import Editor, TextEditorRevealType
from pytoy.ui.vscode.utils import wait_until_true
from pytoy.ui.pytoy_window.models import ViewportMoveMode


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

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None:
        uris = self.editor.get_clean_target_uris_for_unique(within_tabs=within_tabs, within_windows=within_windows)
        documents = [Document(uri=uri) for uri in uris]
        buffers = [PytoyBufferVSCode(doc) for doc in documents]
        for buffer in buffers:
            buffer.init_buffer(content="")
        self.editor.unique(within_tabs=within_tabs, within_windows=within_windows)

    @property
    def cursor(self) -> CursorPosition:
        position  = self.editor.cursor_position
        if position:
            line, col = position
        else:
            raise RuntimeError("cursor cannot be obtained.") 
        return CursorPosition(line - 1, col)

    _REVEAL_TYPE_MAP = {
        ViewportMoveMode.NONE: TextEditorRevealType.Default,
        ViewportMoveMode.ENSURE_VISIBLE: TextEditorRevealType.InCenterIfOutsideViewport,
        ViewportMoveMode.CENTER: TextEditorRevealType.InCenter,
        ViewportMoveMode.TOP: TextEditorRevealType.AtTop,
    }

    def move_cursor(self, cursor: CursorPosition,
                    viewport_mode: ViewportMoveMode = ViewportMoveMode.NONE) -> None:
        editor = self.editor
        line, col = cursor.line, cursor.col
        reveal_type = self._REVEAL_TYPE_MAP[viewport_mode]
        editor.set_cursor_position(line + 1, col, reveal_type)


class PytoyWindowProviderVSCode(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        return PytoyWindowVSCode(Editor.get_current())

    def get_windows(self, only_normal_buffers: bool=True) -> Sequence[PytoyWindowProtocol]:
        editors = self._get_editors()
        windows = [PytoyWindowVSCode(elem) for elem in editors]
        if only_normal_buffers: 
            windows = [win for win in windows if win.buffer.is_normal_type]
        return windows 

    def _get_editors(self):
        editors = Editor.get_editors()
        uris = set(BufferURISolver.get_uri_to_bufnr())
        return [elem for elem in editors if elem.uri in uris]

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

        # path: (__pystdout__), `scheme`
        vim.command("noautocmd Vsplit" if mode == "vertical" else "noautocmd Split")
        vim.command(f"Edit {bufname}")
        wait_until_true(lambda: _current_uri_check(bufname), timeout=1.0)
        uri = api.eval_with_return(
            "vscode.window.activeTextEditor.document.uri", with_await=False
        )
        editor = Editor.get_current()
        editor.unique(within_tabs=True,  within_windows=False)
        current.focus()
        # The below is mandatory to syncronize  neovim and vscode
        uri = Uri(**uri)
        wait_until_true(lambda: BufferURISolver.get_bufnr(uri) is not None, timeout=1.0)
        return PytoyWindowVSCode(editor)


    def _get_window_by_bufname(
        self, bufname: str, *, scheme: str = "untitled", 
    ) -> PytoyWindowVSCode | None:
        assert scheme == "untitled"
        editors = Editor.get_editors()
        buf_uri = Uri(path=bufname, scheme=scheme, authority="")
        for editor in editors:
            if editor.document.uri == buf_uri:
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
