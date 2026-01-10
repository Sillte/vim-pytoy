from __future__ import annotations
from pytoy.infra.core.models import Event
from pytoy.ui.pytoy_window.protocol import PytoyWindowID, WindowEvents
from dataclasses import dataclass
from typing import Self, TYPE_CHECKING
from pytoy.ui.vscode.editor import Editor
import vim


from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pytoy.ui.vscode.uri import Uri


class WindowURISolver:

    @classmethod
    def to_uri(cls, winid: int) -> Uri | None:
        bufnr = int(vim.eval(f"winbufnr({winid})"))
        return BufferURISolver.get_bufnr_to_uris().get(bufnr)

    @classmethod
    def from_uri(cls, uri: Uri) -> int | None:
        bufnr = BufferURISolver.get_bufnr(uri)
        if not bufnr:
            return None
        ret =  int(vim.eval(f"bufwinid({bufnr})"))
        if ret == -1:
            return None
        return ret


if TYPE_CHECKING: 
    from pytoy.contexts.vscode import GlobalVSCodeContext

class VSCodeWindowKernel[MortalEntityProtocol]:
    def __repr__(self):
        return f"WindowKernel({self._winid=})"
    
    def __init__(self, winid: int, *, ctx: GlobalVSCodeContext | None = None):
        from pytoy.contexts.vscode import GlobalVSCodeContext
        if ctx is None:
            ctx = GlobalVSCodeContext.get()

        self._winid = winid
        # Value Object.
        self._window_events = WindowEvents.from_winid(self._winid, ctx=ctx.vim_context)

        # URI: must be the unique over the lifetype of `vim.Window`.

        uri = self.uri
        if uri is None:
            raise RuntimeError(f"Given `{winid=}` is invalid.")
        self._snapped_uri: Uri | None = uri # This is for debug purpose.



    @property
    def entity_id(self) -> int:
        return self._winid

    @property
    def on_end(self) -> Event[int]:
        return self._window_events.on_closed

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VSCodeWindowKernel):
            return False
        return other.winid == self.winid

    @property
    def winid(self) -> int:
        return self._winid

    @property
    def uri(self) -> Uri | None:
        return WindowURISolver.to_uri(self.winid)


    @property
    def editor(self) -> Editor | None:
        """It returns one of `Editor` which can correspond to `self._winid`. 
        """
        editors = self.editors
        if not editors:
            return None
        elif len(editors) == 1:
            return editors[0]
        else:
            """NOTE:
            Multiple editors may correspond to a single Vim window.
            This implementation arbitrarily selects the first one.
            """
            return editors[0]

    @property
    def editors(self) -> list[Editor]:
        uri = WindowURISolver.to_uri(self.winid)
        return [editor for editor in Editor.get_editors() if editor.uri == uri]

    @property
    def valid(self) -> bool:
        return bool(self.editor)

    @property
    def on_closed(self) -> Event[PytoyWindowID]:
        return self._window_events.on_closed

    @property
    def events(self) -> WindowEvents:
        return self._window_events