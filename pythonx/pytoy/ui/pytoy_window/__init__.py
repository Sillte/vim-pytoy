from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.ui_enum import get_ui_enum, UIEnum


class PytoyWindow(PytoyWindowProtocol):
    def __init__(self, impl: PytoyWindowProtocol):
        self._impl = impl

    @property
    def valid(self) -> bool:
        return self.impl.valid

    @property
    def buffer(self) -> PytoyBuffer:
        return self.impl.buffer

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

    def focus(self) -> bool:
        return self.impl.focus()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PytoyWindow):
            return NotImplemented
        return self.impl.__eq__(other)

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


class PytoyWindowProvider(PytoyWindowProviderProtocol):
    def __init__(self, impl: PytoyWindowProviderProtocol | None = None):
        if impl is None:
            ui_enum = get_ui_enum()
            if ui_enum == UIEnum.VSCODE:
                from pytoy.ui.pytoy_window.impl_vscode import PytoyWindowProviderVSCode

                impl = PytoyWindowProviderVSCode()
            else:
                from pytoy.ui.pytoy_window.impl_vim import PytoyWindowProviderVim

                impl = PytoyWindowProviderVim()
        self._impl = impl

    @property
    def impl(self) -> PytoyWindowProviderProtocol:
        return self._impl

    def get_current(self) -> PytoyWindowProtocol:
        return self._impl.get_current()

    def get_windows(self) -> list[PytoyWindowProtocol]:
        return self._impl.get_windows()

    def create_window(
        self,
        bufname: str,
        mode: str = "vertical",
        base_window: PytoyWindowProtocol | None = None,
    ) -> PytoyWindowProtocol:
        return self.impl.create_window(bufname, mode, base_window)
