from dataclasses import dataclass, field
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.core.models.event import Event

from typing import Callable, Literal, Sequence, Protocol,  Hashable, Any, Self

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
    impl_is_busy: None | Callable[[list[int], Snapshot], bool | None] = None
    impl_interrupt: None | Callable[[int, list[int]], None | InputOperation] = None
    
    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool | None:
        if self.impl_is_busy:
            return self.impl_is_busy(children_pids, snapshot)
        return 

    def interrupt(self, pid: int, children_pids: list[int]) -> None | InputOperation:
        if self.impl_interrupt:
            return self.impl_interrupt(pid, children_pids)
        return 
    
    @classmethod
    def with_command_wrapper(cls, impl: TerminalDriverProtocol,  command_wrapper: Callable[[str], list[str]]) -> Self: 
        new_command = command_wrapper(impl.command)
        return cls(command=" ".join(new_command),
                   name=impl.name, 
                   make_operations=impl.make_operations,
                   eol=impl.eol, 
                   impl_is_busy=impl.is_busy,
                   impl_interrupt=impl.interrupt,
                   )
    

@dataclass
class ConsoleConfiguration:
    lines: int | None = None
    cols: int | None = None


@dataclass(frozen=True)
class TerminalJobRequest:
    driver: TerminalDriverProtocol
    name: str = "default"
    on_exit: Callable[[Any], None] | None = None
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


