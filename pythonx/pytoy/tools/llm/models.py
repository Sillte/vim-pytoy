import uuid 
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from pytoy.infra.core.models import Event
from pytoy.ui.pytoy_buffer import PytoyBuffer

from pytoy.infra.timertask.thread_executor import ThreadExecution

type PreSaveHook = Callable[[PytoyBuffer], None]

@dataclass
class HooksForInteraction:
    ...
    # Currently, this is not used.
    # pre_save: PreSaveHook | None = None


@dataclass
class LLMInteraction:
    thread_execution: ThreadExecution
    on_exit: Event[Any]
    id: str = field(default_factory=lambda: str(uuid.uuid1()))
    timestamp: float = field(default_factory=lambda: time.time())
    hooks: HooksForInteraction | None = None
