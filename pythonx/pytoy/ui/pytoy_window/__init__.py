from pathlib import Path
from pytoy.ui.pytoy_window.protocol import (
    PytoyWindowProtocol,
    PytoyWindowProviderProtocol,
)
from pytoy.ui.pytoy_window.models import ViewportMoveMode, BufferSource, WindowCreationParam
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.ui_enum import get_ui_enum, UIEnum

from pytoy.infra.core.models import CursorPosition, CharacterRange, LineRange
from pytoy.infra.core.models.event import Event
from typing import Sequence, Literal

from pytoy.ui.pytoy_window.facade import PytoyWindowProvider, PytoyWindow

