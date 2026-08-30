from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Hashable, Protocol

from pytoy.shared.lib.event.domain import Event
from pytoy.tool_execution.terminal.contract.models import Snapshot, TerminalDriverProtocol

type JobID = Hashable


@dataclass(frozen=True)
class JobEvents:
    on_job_exit: Event[Any]
    on_update: Event[int]


class TerminalJobProtocol(Protocol):
    def start(self) -> None: ...

    @property
    def job_id(self) -> JobID | None: ...

    @property
    def name(self) -> str: ...

    @property
    def cwd(self) -> Path: ...

    @property
    def alive(self) -> bool: ...

    def send(self, input: str, /) -> None: ...

    def interrupt(self) -> None: ...

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


@dataclass
class ConsoleConfiguration:
    lines: int | None = None
    cols: int | None = None


@dataclass(frozen=True)
class TerminalJobRequest:
    driver: TerminalDriverProtocol
    name: str = "default"
    console: ConsoleConfiguration = field(default_factory=lambda: ConsoleConfiguration())


@dataclass(frozen=True)
class SpawnOption:
    cwd: str | Path | None = None
    env: dict[str, str] | None = None
