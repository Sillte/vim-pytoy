from __future__ import annotations
from typing import Sequence, TYPE_CHECKING
from pytoy.shared.ui.status_line.models import StatusLineItem
from pytoy.shared.ui.status_line.protocol import StatusLineManagerProtocol
from pytoy.shared.lib.backend import get_backend_enum, BackendEnum
if TYPE_CHECKING:
    from pytoy.shared.ui.pytoy_window.protocol import WindowEvents


class StatusLineManager(StatusLineManagerProtocol):
    def __init__(self,  events: "WindowEvents", *, impl: StatusLineManagerProtocol | None = None):
        if impl is None:
            impl = _get_impl(events)
        self._impl = impl
        
    @property
    def impl(self) -> StatusLineManagerProtocol:
        return self._impl

    def register(self, item: StatusLineItem) -> StatusLineItem:
        return self._impl.register(item)

    def deregister(self, item: StatusLineItem, strict_error=False) -> bool:
        return self._impl.deregister(item, strict_error=strict_error)

    @property
    def items(self) -> Sequence[StatusLineItem]:
        return self._impl.items


def _get_impl(events: "WindowEvents") -> StatusLineManagerProtocol:
    """Get the appropriate StatusLineManager implementation based on the UI environment."""
    backend_enum = get_backend_enum()
    
    if backend_enum in (BackendEnum.VIM, BackendEnum.NVIM, BackendEnum.VSCODE):
        from pytoy.shared.ui.status_line.impl_vim import StatusLineManagerVim
        return StatusLineManagerVim(events)
    else:
        from pytoy.shared.ui.status_line.impl_dummy import StatusLineManagerDummy
        return StatusLineManagerDummy()