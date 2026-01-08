# **Specification**
# * Editor: Editor of VSCode.
# * Editor of PytoyWindow: the buffers of windows is managed in neovim.

from pathlib import Path
from pytoy.infra.core.models import CursorPosition, CharacterRange, LineRange
from pytoy.infra.core.models import Event
from pytoy.ui.pytoy_window.impls.vscode.kernel import WindowURISolver
from pytoy.ui.pytoy_window.impls.vscode.kernel import VSCodeWindowKernel
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pytoy.ui.vscode.editor.models import TextEditorRevealType
from pytoy.ui.vscode.uri import Uri
import vim  # (vscode-neovim extention)
from typing import Sequence, Literal, assert_never, cast
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer.impls.vscode import PytoyBufferVSCode
from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
    PytoyWindowID,
)
from pytoy.ui.vscode.document import Api, Document
from pytoy.ui.vscode.editor import Editor
from pytoy.ui.vscode.utils import wait_until_true
from pytoy.ui.pytoy_window.models import ViewportMoveMode, BufferSource, WindowCreationParam

from pytoy.ui.pytoy_window.vim_window_utils import get_last_selection
from pytoy.infra.core.entity import EntityRegistry, MortalEntityProtocol, EntityRegistryProvider
from ...vim_window_utils import VimWinIDConverter


kernel_registry: EntityRegistry = EntityRegistryProvider.get(VSCodeWindowKernel)


class PytoyWindowVSCode(PytoyWindowProtocol):
    def __init__(self, winid: int, *, kernel_registry: EntityRegistry = kernel_registry):
        self._kernel = kernel_registry.get(winid)
        
    @property
    def winid(self) -> PytoyWindowID:
        return self._kernel.winid
        
    @property
    def editor(self) -> Editor:
        editor = self._kernel.editor
        if editor is None:
            raise ValueError(f"Editor does not exist, {self._kernel}")
        return editor

    @property
    def kernel(self) -> VSCodeWindowKernel:
        return self._kernel

    @property
    def uri(self) -> Uri:
        return self._kernel.uri


    @property
    def buffer(self) -> PytoyBuffer:
        impl = PytoyBufferVSCode.from_document(self.editor.document)
        return PytoyBuffer(impl)

    @property
    def valid(self) -> bool:
        return self._kernel.valid

    def is_left(self) -> bool:
        return self.editor.viewColumn == 1

    def close(self) -> bool:
        return self.editor.close()

    def focus(self) -> bool:
        if self.kernel.editor:
           self.kernel.editor.focus()
           return True
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PytoyWindowVSCode):
            return NotImplemented
        return self.editor == other.editor

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None:
        uris = self.editor.get_clean_target_uris_for_unique(within_tabs=within_tabs, within_windows=within_windows)
        uri_to_bufnr = BufferURISolver.get_uri_to_bufnr()
        bufnrs = set(bufnr for uri in uris if (bufnr:=uri_to_bufnr.get(uri)))
        buffers = [PytoyBufferVSCode(bufnr) for bufnr in bufnrs]
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
        if not self.winid:
            return CharacterRange(self.cursor, self.cursor)
        selection = get_last_selection(self.winid)
        if selection:
            return selection
        return CharacterRange(self.cursor, self.cursor)


    @property
    def selected_line_range(self) -> LineRange:
        return self.selection.as_line_range()

    @property
    def on_closed(self) -> Event[PytoyWindowID]:
        return self._kernel.on_closed


class PytoyWindowProviderVSCode(PytoyWindowProviderProtocol):
    def get_current(self) -> PytoyWindowProtocol:
        uri = Editor.get_current().uri
        winid = WindowURISolver.from_uri(uri)
        if winid is None:
            raise RuntimeError(f"Current Window does not exist. {uri=}")
        return PytoyWindowVSCode(winid)

    def get_windows(self, only_normal_buffers: bool=True) -> Sequence[PytoyWindowProtocol]:
        winids = [VimWinIDConverter.from_vim_window(window) for window in vim.windows]
        windows = [PytoyWindowVSCode(winid) for winid in winids]
        if only_normal_buffers: 
            windows = [win for win in windows if win.kernel.editor and win.buffer.is_normal_type]
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

        uri = self._to_uri(source.name, type=source.type)
        if param.try_reuse:
            if (winid := WindowURISolver.from_uri(uri)):
                window =  PytoyWindowVSCode(winid)
                if param.cursor:
                    window.move_cursor(param.cursor)
                return window

        current =  self.get_current()
        #current_editor = current.editor
        editor = self._create_editor(source, param)
        if not current.focus():
            print(f"{current} cannot be focused.")
        flag = wait_until_true(lambda: WindowURISolver.from_uri(editor.uri) is not None, timeout=1.0)
        winid = WindowURISolver.from_uri(uri)
        if not winid:
            raise RuntimeError(f"Synchronization of `{uri=}` and `winid` failed. ", flag) 
        return PytoyWindowVSCode(winid)


    def _create_editor(self,
                       source: BufferSource, 
                       param: WindowCreationParam) -> Editor:
        anchor = param.anchor
        if anchor is None:
            anchor = PytoyWindowProviderVSCode().get_current()
        anchor = cast(PytoyWindowVSCode, anchor)

        anchor.focus()
        uri = self._to_uri(source.name, type=source.type)

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

    def _to_uri(self, bufname: str, *, type: Literal["file", "nofile"] = "nofile",) -> Uri:
        match type: 
            case "file":
                query_uri = Uri.from_filepath(bufname)
            case "nofile":
                query_uri = Uri.from_untitled_name(bufname)
            case _:
                assert_never(type)
        return query_uri

