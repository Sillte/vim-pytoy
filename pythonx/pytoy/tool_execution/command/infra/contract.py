from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pytoy.shared.lib.event import Event

from .models import JobID, JobResult, Snapshot


@dataclass(frozen=True)
class JobEvents:
    on_job_exit: Event[JobResult]
    on_update_stdout_line: Event[str]
    on_update_stderr_line: Event[str]


class OutputJobProtocol(Protocol):
    def start(self) -> None: ...

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


__all__ = ["JobEvents", "JobID", "OutputJobProtocol"]
