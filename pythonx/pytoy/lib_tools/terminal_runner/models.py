from dataclasses import dataclass, field
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.core.models.event import Event

from typing import Callable, Literal, Sequence, Protocol,  Hashable, Any

from pathlib import Path

type ReturnCode = int
type JobID = Hashable


@dataclass(frozen=True)
class ConsoleSnapshot:
    lines: int 
    cols: int 
    content: str

@dataclass(frozen=True)
class Snapshot:
    timestamp: float
    console: ConsoleSnapshot
    cursor: CursorPosition
    
    @property
    def content(self) -> str:
        return self.console.content

@dataclass
class WaitOperation:
    time: float = 0.5 

type InputOperation = WaitOperation | str

type TerminalName = str
type CommandStr = str
type Pid = int
type ChildrenPids = list[int]
type InputStr = str

class TerminalDriverProtocol(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def command(self) -> str: ...
    @property
    def eol(self) -> str | None: ...

    def is_busy(self, children_pids: ChildrenPids, snapshot: Snapshot, /) -> bool | None: ...
    def make_operations(self, input_str: str, /) -> Sequence[InputOperation]: ...
    def interrupt(self, pid: int, children_pids: ChildrenPids, /) -> None | InputOperation: ...

        
@dataclass(frozen=True)
class TerminalDriver:
    name: CommandStr
    command: str
    make_operations: Callable[[str], Sequence[InputOperation]] 
    eol: str | None  = None
    
    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool | None:
        return 

    def interrupt(self, pid: int, children_pids: list[int]) -> None | InputOperation:
        return 
    



@dataclass
class ConsoleConfiguration:
    lines: int | None = None
    cols: int | None = None


@dataclass(frozen=True)
class TerminalJobRequest:
    driver: TerminalDriverProtocol
    name: str = "default"
    on_exit: Callable[[Any], None] | None = None
    # Note: ConsoleConfiguration is no applicable in nvim.
    console: ConsoleConfiguration = field(default_factory=lambda :ConsoleConfiguration())

@dataclass(frozen=True)
class SpawnOption:
    cwd: str | Path | None = None
    env: dict[str, str] | None = None 


@dataclass(frozen=True)
class JobEvents:
    on_job_exit: Event[Any]
    on_update: Event[int]


class TerminalJobProtocol(Protocol):
    @property
    def job_id(self) -> JobID | None:
        ...

    @property
    def name(self) -> str:
        ...

    @property
    def cwd(self) -> Path:
        ...
        

    @property
    def alive(self) -> bool:
        ...

    def send(self, input: str, /) -> None:
        ...

    def interrupt(self) -> None:
        ...

    def terminate(self) -> None:
        ...

    def dispose(self) -> None:
        ...

    @property
    def snapshot(self) -> Snapshot:
        ...

    @property
    def pid(self) -> int:
        ...

    @property
    def children_pids(self) -> list[int]:
        ...

    @property
    def events(self) -> JobEvents:
        ...


