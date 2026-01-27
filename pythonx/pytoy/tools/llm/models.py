import uuid 
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from pytoy.infra.core.models import Event
from pytoy.ui.pytoy_buffer import PytoyBuffer

type PreSaveHook = Callable[[PytoyBuffer], None]

@dataclass
class HooksForInteraction:
    ...
    # Currently, this is not used.
    # pre_save: PreSaveHook | None = None


@dataclass
class LLMInteraction:
    task: Any
    on_exit: Event[Any]
    id: str = field(default_factory=lambda: str(uuid.uuid1()))
    timestamp: float = field(default_factory=lambda: time.time())
    hooks: HooksForInteraction | None = None
