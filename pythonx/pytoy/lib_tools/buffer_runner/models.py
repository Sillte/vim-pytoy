from dataclasses import dataclass, field
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.core.models.event import Event

from typing import Callable, Literal, Sequence, Protocol, Literal, Hashable, Any

from pathlib import Path

type ReturnCode = int
type JobID = Hashable


@dataclass
class OutputJobRequest:
    command: str  | Sequence[str] # Execution
    name: str = "default"
    outputs: Sequence[Literal["stdout", "stderr"]] = ("stdout", "stderr")
    # What output is used. 
    # E.g. (Wrap the command for envrionement, e.g. for example, in case of `uv`, `uv run ...`)
    command_wrapper: Callable[..., Sequence[str]] | None = None
    on_exit: Callable[[Any], None] | None = None


@dataclass
class SpawnOption:
    cwd: str | Path | None = None
    env: dict[str, str] | None = None 



@dataclass(frozen=True)
class JobEvents:
    # Basically, update is one line 
    on_job_exit: Event[Any]
    on_update_stdout_line: Event[str]
    on_update_stderr_line: Event[str]


@dataclass
class Snapshot:
    timestamp: float
    stdout: str
    stderr: str
    name: str


class OutputJobProtocol(Protocol):
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

