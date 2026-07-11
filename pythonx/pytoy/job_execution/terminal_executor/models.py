from pytoy.job_execution.terminal_runner import TerminalJobRunner
from pytoy.job_execution.terminal_runner.models import TerminalDriverProtocol
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer

from pytoy.job_execution.terminal_runner.models import TerminalJobRequest, SpawnOption, JobID, Event, JobEvents
from pytoy.job_execution.terminal_runner.models import TerminalDriver
from pytoy.job_execution.terminal_runner.models import ExecutionWrapperType


from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Self


type ExecutionID = JobID
type ExecutionEvents = JobEvents

type DriverKind = str


@dataclass(frozen=True)
class BufferRequest:
    source: BufferSource

    @classmethod
    def from_str(cls, source: str) -> Self:
        return cls(source=BufferSource.from_str(source))

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        return cls(source=BufferSource.from_path(Path(path)))

    @classmethod
    def from_no_file(cls, name: str) -> Self:
        return cls(source=BufferSource.from_no_file(name))

    @classmethod
    def from_buffer(cls, buffer: PytoyBuffer) -> Self:
        return cls(source=buffer.source)


@dataclass(frozen=True)
class ExecutionRequest:
    driver: TerminalDriverProtocol
    command_wrapper: ExecutionWrapperType | None = None
    cwd: str | Path | None = None
    env: dict[str, str] | None = None


@dataclass(frozen=True)
class TerminalExecution:
    runner: TerminalJobRunner
    driver: TerminalDriverProtocol
    cwd: Path
    id: ExecutionID

    @property
    def events(self) -> ExecutionEvents:
        return self.runner.events


@dataclass(frozen=True)
class ExecutionHooks:
    on_finish: Callable[[Any], None] | None = None
    on_start: Callable[["TerminalExecution"], None] | None = None

    @staticmethod
    def merge(hook1: "ExecutionHooks", hook2: "ExecutionHooks") -> "ExecutionHooks":
        from dataclasses import fields

        merged_kwargs = {}
        for item in fields(ExecutionHooks):
            f1 = getattr(hook1, item.name)
            f2 = getattr(hook2, item.name)

            if not f1:  # (f1= None, f2=None), (f1=None, f2=Callable)
                merged_kwargs[item.name] = f2
            elif not f2:  # (f1=Callable, f2=None)
                merged_kwargs[item.name] = f1
            else:

                def _merged(f1=f1, f2=f2):
                    return lambda *a, **k: (f1(*a, **k), f2(*a, **k))

                merged_kwargs[item.name] = _merged()
        return ExecutionHooks(**merged_kwargs)


@dataclass(frozen=True)
class ExecutionContext:
    """This should be used for repeating the same `Application` again."""

    buffer_source: BufferSource
    execution_request: ExecutionRequest
    hooks: ExecutionHooks
    kind: DriverKind


@dataclass(frozen=True)
class ExecutionPolicy:
    buffer_request: BufferRequest
    kind: DriverKind | None = None


@dataclass(frozen=True)
class ExecutionQuery:
    buffer: BufferSource | None = None
    kind: DriverKind | None = None
