# **Specification**
# * Editor: Editor of VSCode.
# * Editor of PytoyWindow: the buffers of windows is managed in neovim.


from pathlib import Path
from pytoy.infra.core.models import CursorPosition, CharacterRange, LineRange
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pytoy.ui.vscode.editor.models import TextEditorRevealType
from pytoy.ui.vscode.uri import Uri
import vim  # (vscode-neovim extention)
from typing import Sequence, Literal, assert_never, cast
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode
from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.ui.vscode.document import Api, Document
from pytoy.ui.vscode.editor import Editor
from pytoy.ui.vscode.utils import wait_until_true
from pytoy.ui.pytoy_window.models import ViewportMoveMode, BufferSource, WindowCreationParam

from pytoy.ui.pytoy_window.vim_window_utils import get_last_selection


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
        return CursorPosition(line, col)

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
        editor.set_cursor_position(line, col, reveal_type)

    @property
    def selection(self) -> CharacterRange:
        winid = self._to_winid()
        if not winid:
            return CharacterRange(self.cursor, self.cursor)
        selection = get_last_selection(winid)
        if selection:
            return selection
        return CharacterRange(self.cursor, self.cursor)

    
    def _to_winid(self) -> int | None:
        bufnr = BufferURISolver.get_bufnr(self.editor.uri)
        if not bufnr:
            return None
        winid = vim.eval(f"win_findbuf({bufnr})[0]")
        return winid


    @property
    def selected_line_range(self) -> LineRange:
        return self.selection.as_line_range()


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

    def open_window(self,
                    source: str | Path | BufferSource,
                    param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] = "in-place") -> PytoyWindowProtocol:
        source = source if isinstance(source, BufferSource) else BufferSource.from_any(source)
        param = param if isinstance(param, WindowCreationParam) else WindowCreationParam.from_literal(param)

        if param.try_reuse:
            if editor:= self._get_editor_by_bufname(source.name, type=source.type):
                window =  PytoyWindowVSCode(editor)
                if param.cursor:
                    window.move_cursor(param.cursor)

        current = self.get_current()
        editor = self._create_editor(source, param)
        flag = wait_until_true(lambda: BufferURISolver.get_bufnr(editor.uri) is not None, timeout=1.0)
        current.focus()
        return PytoyWindowVSCode(editor)


    def _create_editor(self,
                       source: BufferSource, 
                       param: WindowCreationParam) -> Editor:
        anchor = param.anchor
        if anchor is None:
            anchor = PytoyWindowProviderVSCode().get_current()
        anchor = cast(PytoyWindowVSCode, anchor)

        anchor.focus()

        # generation of uri
        match source.type:
            case "file":
                uri = Uri.from_filepath(source.name)
            case "nofile":
                uri = Uri.from_untitled_name(source.name)
            case _:
                assert_never(source.type)

        if param.target == "in-place":
            editor = anchor.editor.show(uri)
            if param.cursor:
                line, col = param.cursor.line, param.cursor.col
                editor.set_cursor_position(line, col, TextEditorRevealType.InCenterIfOutsideViewport)
            return editor
        if param.target == "split":
            match param.split_direction:
                case "horizontal":
                    direction = "horizontal"
                case "vertical":
                    direction = "vertical"
                case None:
                    raise ValueError("None is invalid.")
                case _:
                    assert_never(param.split_direction)

            if param.cursor:
                pos = param.cursor.line, param.cursor.col
            else:
                pos = None
            return Editor.create(uri, direction, cursor=pos)

        raise RuntimeError("Implementation Error") 


    def _get_editor_by_bufname(
        self, bufname: str, *, type: Literal["file", "nofile"] = "nofile", 
    ) -> Editor | None:
        editors = Editor.get_editors()
        match type: 
            case "file":
                query_uri = Uri.from_filepath(bufname)
            case "nofile":
                query_uri = Uri.from_untitled_name(bufname)
            case _:
                assert_never(type)
        for editor in editors:
            if editor.document.uri == query_uri:
                return editor
        return None


