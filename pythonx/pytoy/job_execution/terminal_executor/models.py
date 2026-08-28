from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Self

from pytoy.job_execution.terminal_runner import TerminalJobRunner
from pytoy.job_execution.terminal_runner.models import (
    CommandExecutionWrapperType,
    JobEvents,
    JobID,
    SpawnOption,
    TerminalDriverProtocol,
    TerminalJobRequest,
)
from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer

type TerminalExecutionID = JobID
type TerminalExecutionEvents = JobEvents

type TerminalDriverKind = str


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
class TerminalExecutionRequest:
    driver: TerminalDriverProtocol | TerminalDriverKind
    command_wrapper: CommandExecutionWrapperType | None = None
    cwd: str | Path | None = None
    env: dict[str, str] | None = None


@dataclass(frozen=True)
class TerminalExecutionHooks:
    on_finish: Callable[[Any], None] | None = None

    @staticmethod
    def merge(hook1: "TerminalExecutionHooks", hook2: "TerminalExecutionHooks") -> "TerminalExecutionHooks":
        from dataclasses import fields

        merged_kwargs = {}
        for item in fields(TerminalExecutionHooks):
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
        return TerminalExecutionHooks(**merged_kwargs)


@dataclass(frozen=True)
class TerminalExecution:
    runner: TerminalJobRunner
    driver: TerminalDriverProtocol
    cwd: Path
    request: TerminalExecutionRequest
    buffer_request: BufferRequest
    env: dict[str, str] | None = None
    id: TerminalExecutionID = field(default_factory=lambda: uuid.uuid4())
    exit_emitter: EventEmitter[Any] = field(default_factory=EventEmitter)

    @property
    def kind(self) -> str:
        return self.driver.kind

    @property
    def on_exit(self) -> Event[Any]:
        return self.exit_emitter.event

    def start(self, hooks: TerminalExecutionHooks) -> None:

        def _on_exit(result: Any, *, hooks: TerminalExecutionHooks) -> None:
            def _call_if_possible(func: Callable[[Any], None] | None):
                if func:
                    func(result)

            _call_if_possible(hooks.on_finish)

        job_request = TerminalJobRequest(driver=self.driver, on_exit=lambda result: _on_exit(result, hooks=hooks))

        spawn_option = SpawnOption(cwd=self.cwd, env=self.env)
        self.runner.run(job_request, spawn_option)
        self.runner.events.on_job_exit.subscribe(lambda value: self.exit_emitter.fire(value))


@dataclass(frozen=True)
class TerminalExecutionContext:
    """This should be used for repeating the same `Application` again."""

    buffer_source: BufferSource
    execution_request: TerminalExecutionRequest
    hooks: TerminalExecutionHooks
    kind: TerminalDriverKind


@dataclass(frozen=True)
class TerminalExecutionPolicy:
    buffer_request: BufferRequest
    kind: TerminalDriverKind | None = None


@dataclass(frozen=True)
class TerminalExecutionQuery:
    buffer: BufferSource | None = None
    kind: TerminalDriverKind | None = None

    @classmethod
    def from_any(cls, buffer: str | Path | BufferSource | None = None, kind: TerminalDriverKind | None = None) -> Self:
        if buffer is not None:
            buffer = BufferSource.from_any(buffer)
        return cls(buffer=buffer, kind=kind)
