from dataclasses import dataclass, field
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.core.models.event import Event

from typing import Callable, Literal, Sequence, Protocol, Literal, Hashable, Any, Mapping

from pathlib import Path

type ReturnCode = int
type JobID = Hashable


@dataclass
class Snapshot:
    timestamp: float
    stdout: str
    stderr: str
    name: str
    
@dataclass(frozen=True)
class JobResult:
    job_id: JobID
    status: int
    snapshot: Snapshot
    
    @property
    def stdout(self) -> str:
        return self.snapshot.stdout

    @property
    def stderr(self) -> str:
        return self.snapshot.stderr

    @property
    def success(self) -> bool:
        return self.status == 0

@dataclass
class OutputJobRequest:
    command: str  | list[str] | tuple[str] # Execution
    name: str = "default"
    # What output is used. 
    # E.g. (Wrap the command for envrionement, e.g. for example, in case of `uv`, `uv run ...`)
    # [TODO]: This is not necessary.
    on_exit: Callable[[JobResult], None] | None = None

    # [TODO]: In normal cases, these `outputs` are invariant settings.
    outputs: Sequence[Literal["stdout", "stderr"]] = ("stdout", "stderr") 


@dataclass(frozen=True)
class SpawnOption:
    cwd: str | Path | None = None
    env: Mapping[str, str] | None = None 



@dataclass(frozen=True)
class JobEvents:
    # Basically, update is one line 
    on_job_exit: Event[JobResult]
    on_update_stdout_line: Event[str]
    on_update_stderr_line: Event[str]




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

