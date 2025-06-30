"""

This module is intended to provide the common interface of ui.

* vim
* neovim
* neovim+vscode

Usage: BufferExecutor:

"""

from pytoy.ui.ui_enum import UIEnum, get_ui_enum #  NOQA
from pytoy.ui.pytoy_buffer import PytoyBuffer, make_buffer, make_duo_buffers  # NOQA
from pytoy.ui.pytoy_quickfix import PytoyQuickFix, handle_records # NOQA



store_cursor = None  # Contextmanager. It retains the cursor in the context.

if get_ui_enum() == UIEnum.VSCODE:
    from pytoy.ui.vscode.focus_controller import store_focus 
    store_cursor = store_focus
else:
    from pytoy.ui.vim import store_window
    store_cursor = store_window



