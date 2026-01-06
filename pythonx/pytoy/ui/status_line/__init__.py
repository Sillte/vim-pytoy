from typing import Sequence
from pytoy.ui.status_line.models import StatusLineItem
from pytoy.ui.status_line.protocol import StatusLineManagerProtocol
from pytoy.ui.ui_enum import get_ui_enum, UIEnum


class StatusLineManager(StatusLineManagerProtocol):
    def __init__(self,  impl: StatusLineManagerProtocol | None = None):
        if impl is None:
            impl = _get_impl()
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


def _get_impl() -> StatusLineManagerProtocol:
    """Get the appropriate StatusLineManager implementation based on the UI environment."""
    ui_enum = get_ui_enum()

    if ui_enum == UIEnum.VIM or ui_enum == UIEnum.NVIM:
        import vim
        from pytoy.ui.status_line.impl_vim import StatusLineManagerVim
        window = vim.current.window
        return StatusLineManagerVim(window)
    elif ui_enum == UIEnum.VSCODE:
        # Currenty, rely on the mechanism of `neovim-vscode` extension.
        import vim
        from pytoy.ui.status_line.impl_vim import StatusLineManagerVim
        window = vim.current.window
        return StatusLineManagerVim(vim.current.window)
    else:
        raise ValueError(f"Unknown UI environment: {ui_enum}")

