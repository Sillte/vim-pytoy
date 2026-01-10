from dataclasses import dataclass, field
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.core.models.event import Event

from typing import Callable  , Literal, Sequence
from pathlib import Path


@dataclass
class ConsoleConfigration:
    width: int 
    height: int 


@dataclass
class SpawnOption:
    cwd: str | Path | None = None
    env: dict[str, str] | None = None 

@dataclass
class ConsoleConfigurationRequest:
    width: int | None = None
    height: int | None = None

@dataclass
class ConsoleSnapshot:
    timestamp: float
    content: str
    config: ConsoleConfigration
    cursor: CursorPosition

@dataclass
class WaitOperation:
    time: float = 0.5 

type InputOperation = WaitOperation | str
type InputConverter = Callable[[str], Sequence[InputOperation]]


@dataclass(frozen=True)
class ExecutorEvents:
    on_update: Event[int]
    on_job_exit: Event[int]




