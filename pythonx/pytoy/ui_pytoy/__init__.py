"""

This module is intended to provide the common interface of ui.

* vim
* neovim
* neovim+vscode

Usage: executors:

"""

from pytoy.ui_pytoy.ui_enum import UIEnum, get_ui_enum #  NOQA
from pytoy.ui_pytoy.pytoy_buffer import PytoyBuffer, make_buffer, make_duo_buffers  # NOQA
from pytoy.ui_pytoy.pytoy_quickfix import PytoyQuickFix # NOQA

