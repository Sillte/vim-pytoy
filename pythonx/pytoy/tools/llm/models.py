from dataclasses import dataclass
from typing import Callable
from pytoy.ui.pytoy_buffer import PytoyBuffer

type PreSaveHook = Callable[[PytoyBuffer], None]

@dataclass
class HooksForInteraction:
    pre_save: PreSaveHook | None = None