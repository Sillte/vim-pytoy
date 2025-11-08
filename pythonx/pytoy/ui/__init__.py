"""

This module is intended to provide the common interface of ui.

* vim
* neovim
* neovim+vscode

Usage: BufferExecutor:

"""

from pytoy.ui.ui_enum import UIEnum, get_ui_enum  #  NOQA
from pytoy.ui.pytoy_buffer import PytoyBuffer, make_buffer, make_duo_buffers  # NOQA
from pytoy.ui.pytoy_quickfix import PytoyQuickFix, handle_records  # NOQA
from pytoy.ui.utils import to_filename  # NOQA
