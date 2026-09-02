from pathlib import Path
from typing import Literal, Sequence

from pytoy.shared.lib.backend import BackendEnum, get_backend_enum
from pytoy.shared.lib.event.domain import Event
from pytoy.shared.lib.text import CharacterRange, CursorPosition, LineRange
from pytoy.shared.ui.contract.window import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer.models import BufferSource
from pytoy.shared.ui.pytoy_window.models import ViewportMoveMode, WindowCreationParam


class PytoyWindow(PytoyWindowProtocol):
    def __init__(self, impl: PytoyWindowProtocol):
        self._impl = impl

    @property
    def valid(self) -> bool:
        return self.impl.valid

    @property
    def buffer(self) -> PytoyBuffer:
        return PytoyBuffer(self.impl.buffer)

    def close(self) -> bool:
        return self.impl.close()

    def is_left(self) -> bool:
        """Return whether this is leftwindow or not."""
        return self.impl.is_left()

    def unique(self, within_tabs: bool = False, within_windows: bool = True) -> None:
        """Isolate the window.

        NOTE: Unfortunately, due to affairs of vscode,
        this cannot be realiazed with `close` and `__eq__`.
        """
        return self.impl.unique(within_tabs, within_windows=within_windows)

    def deduplicate(self, scope: Literal["buffer"] = "buffer") -> None:
        return self.impl.deduplicate(scope=scope)

    def focus(self) -> bool:
        return self.impl.focus()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PytoyWindow):
            return NotImplemented
        return self.impl == other.impl

    @property
    def cursor(self) -> CursorPosition:
        return self.impl.cursor

    def move_cursor(self, cursor: CursorPosition, viewport_mode: ViewportMoveMode = ViewportMoveMode.NONE) -> None:
        return self.impl.move_cursor(cursor, viewport_mode)

    @property
    def selection(self) -> CharacterRange:
        return self.impl.selection

    @property
    def selected_line_range(self) -> LineRange:
        return self.impl.selected_line_range

    @property
    def on_closed(self) -> Event["PytoyWindowProtocol"]:
        return self.impl.on_closed

    @property
    def status_line_manager(self):
        return self.impl.status_line_manager

    # Below functions are not defined in PytoyWindowProtocol.

    @property
    def impl(self) -> PytoyWindowProtocol:
        return self._impl

    @staticmethod
    def get_current() -> "PytoyWindow":
        impl = PytoyWindowProvider().get_current()
        return PytoyWindow(impl)

    @staticmethod
    def get_windows() -> list["PytoyWindow"]:
        impls = PytoyWindowProvider().get_windows()
        return [PytoyWindow(elem) for elem in impls]

    @staticmethod
    def open(
        source: str | Path | BufferSource,
        param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] = "in-place",
    ) -> "PytoyWindow":
        """Open or create PytoyWindow."""
        return PytoyWindowProvider().open_window(source, param)


class PytoyWindowProvider(PytoyWindowProviderProtocol):
    def __init__(self, impl: PytoyWindowProviderProtocol | None = None):
        if impl is None:
            backend_enum = get_backend_enum()
            if backend_enum == BackendEnum.VSCODE:
                from pytoy.shared.ui.pytoy_window.impls.vscode import PytoyWindowProviderVSCode

                impl = PytoyWindowProviderVSCode()
            elif backend_enum in (BackendEnum.VIM, BackendEnum.NVIM):
                from pytoy.shared.ui.pytoy_window.impls.vim import PytoyWindowProviderVim

                impl = PytoyWindowProviderVim()
            else:
                from pytoy.shared.ui.pytoy_window.impls.dummy import PytoyWindowProviderDummy

                impl = PytoyWindowProviderDummy()
        self._impl = impl

    @property
    def impl(self) -> PytoyWindowProviderProtocol:
        return self._impl

    def get_current(self) -> PytoyWindow:
        return PytoyWindow(self._impl.get_current())

    def get_windows(self, only_normal_buffers: bool = True) -> Sequence[PytoyWindow]:
        return [PytoyWindow(window) for window in self._impl.get_windows(only_normal_buffers=only_normal_buffers)]

    def open_window(
        self,
        source: str | Path | BufferSource,
        param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] = "in-place",
    ) -> PytoyWindow:
        impl_window = self._impl.open_window(source, param)
        return PytoyWindow(impl_window)
