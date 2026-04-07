from pathlib import Path
from pytoy.shared.ui.pytoy_buffer.models import BufferSource
from pytoy.shared.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.shared.ui.pytoy_window.models import ViewportMoveMode, WindowCreationParam
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer

from pytoy.shared.lib.text import CursorPosition, CharacterRange, LineRange
from pytoy.shared.lib.event.domain import Event
from typing import Sequence, Literal

from pytoy.shared.ui.pytoy_window.facade import PytoyWindowProvider, PytoyWindow

