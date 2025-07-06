from pytoy.ui.pytoy_window.protocol import PytoyWindowProtocol, PytoyWindowProviderProtocol
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.ui_enum import get_ui_enum, UIEnum

class PytoyWindow(PytoyWindowProtocol):
    def __init__(self, impl: PytoyWindowProtocol):
        self._impl = impl
        
    @property
    def impl(self) -> PytoyWindowProtocol:
        return self._impl

    @staticmethod
    def get_current() -> "PytoyWindow":
        impl = PytoyWindowProvider().get_current()
        return PytoyWindow(impl)
    
    @property
    def valid(self) -> bool:
        return self.impl.valid

    @property
    def buffer(self) -> PytoyBuffer | None:
        # Implement logic to return the buffer associated with this window
        return self.impl.buffer

    def is_left(self) -> bool:
        """Return whether this is leftwindow or not."""
        return self.impl.is_left()

class PytoyWindowProvider:
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
        
