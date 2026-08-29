from dataclasses import dataclass
from pathlib import Path
from typing import Hashable, Protocol

from pytoy.shared.lib.event import Event

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


@dataclass(frozen=True)
class JobEvents:
    on_job_exit: Event[JobResult]
    on_update_stdout_line: Event[str]
    on_update_stderr_line: Event[str]


class OutputJobProtocol(Protocol):
    @property
    def job_id(self) -> JobID | None: ...

    @property
    def name(self) -> str: ...

    @property
    def cwd(self) -> Path: ...

    @property
    def alive(self) -> bool: ...

    def terminate(self) -> None: ...

    def dispose(self) -> None: ...

    @property
    def snapshot(self) -> Snapshot: ...

    @property
    def pid(self) -> int: ...

    @property
    def children_pids(self) -> list[int]: ...

    @property
    def events(self) -> JobEvents: ...
