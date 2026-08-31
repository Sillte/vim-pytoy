from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Hashable, Literal, Mapping, Sequence

type ReturnCode = int


@dataclass
class OutputJobRequest:
    command: str | list[str] | tuple[str]  # Execution
    name: str = "default"
    # What output is used.
    # E.g. (Wrap the command for envrionement, e.g. for example, in case of `uv`, `uv run ...`)
    # [TODO]: This is not necessary.
    on_exit: Callable[["JobResult"], None] | None = None

    # [TODO]: In normal cases, these `outputs` are invariant settings.
    outputs: Sequence[Literal["stdout", "stderr"]] = ("stdout", "stderr")


@dataclass(frozen=True)
class SpawnOption:
    cwd: str | Path | None = None
    env: Mapping[str, str] | None = None


@dataclass
class Snapshot:
    timestamp: float
    stdout: str
    stderr: str
    name: str


type JobID = Hashable


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
