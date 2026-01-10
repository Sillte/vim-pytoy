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


class TerminalDriverProtocol(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def command(self) -> str:
        """The name of command"""
        ...

    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool | None:
        """Return whether the `terminal` is busy or not.
        Note that sometimes, the estimation is not perfect. (very difficult to realize perfection).
        If the return is True, it is 100% sure that the process is busy,
        If the return is False, it cannot guarantee that the process is NOT working.
        (When we have to rely on the lastline, mis-detection cannot be avoided.)
        """
        ...

    def make_lines(self, input_str: str) -> Sequence[InputOperation]:
        """Make the lines which is sent into `pty`.

        * If `\r` / `\n` is added at the end of elements, they are sent as is.
        * Otherwise, the LF is appended at the end of elements.
        """
        ...

    def interrupt(self, pid: int, children_pids: list[int]) -> None:
        """Interrupt the process. if possible."""
        ...
        

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

    def send(self, input: str) -> None:
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