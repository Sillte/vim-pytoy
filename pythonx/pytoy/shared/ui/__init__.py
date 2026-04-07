"""

This module is intended to provide the common interface of ui.

* vim
* neovim
* neovim+vscode
"""

from pytoy.shared.ui.pytoy_buffer import PytoyBuffer, PytoyBufferProvider, make_buffer, make_duo_buffers  # NOQA
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer, PytoyBufferProvider, make_buffer, make_duo_buffers  # NOQA
from pytoy.shared.ui.pytoy_window import PytoyWindow
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixRecord  # NOQA
from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix, handle_records  # NOQA

