from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Self

from pytoy.job_execution.terminal_runner import TerminalJobRunner
from pytoy.job_execution.terminal_runner.domain.models import (
    CommandWrapperType,
    JobEvents,
    SpawnOption,
    TerminalDriverProtocol,
    TerminalJobRequest,
)
from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.outcome import Error, Outcome, Success, is_success
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer

type TerminalExecutionID = str
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
    command_wrapper: CommandWrapperType | None = None
    cwd: str | Path | None = None
    env: dict[str, str] | None = None


@dataclass(frozen=True)
class TerminalExecutionResult:
    exit_code: int
    buffer: PytoyBuffer


@dataclass(frozen=True)
class TerminalExecutionExit:
    id: TerminalExecutionID
    outcome: Outcome[TerminalExecutionResult, Exception]


@dataclass(frozen=True)
class TerminalExecutionHooks:
    on_result: Callable[[TerminalExecutionResult], None] | None = None
    on_exit_code_zero: Callable[[TerminalExecutionResult], None] | None = None
    on_exit_code_non_zero: Callable[[TerminalExecutionResult], None] | None = None
    on_exception: Callable[[Exception], None] | None = None

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

    @classmethod
    def from_any(
        cls,
        *,
        on_result: Callable[[TerminalExecutionResult], None] | None = None,
        on_exit_code_zero: Callable[[TerminalExecutionResult], None] | None = None,
        on_exit_code_non_zero: Callable[[TerminalExecutionResult], None] | None = None,
        on_exception: Callable[[Exception], None] | None = None,
    ) -> Self:
        return cls(
            on_result=on_result,
            on_exit_code_zero=on_exit_code_zero,
            on_exit_code_non_zero=on_exit_code_non_zero,
            on_exception=on_exception,
        )


@dataclass(frozen=True)
class TerminalExecution:
    runner: TerminalJobRunner
    driver: TerminalDriverProtocol
    cwd: Path
    request: TerminalExecutionRequest
    buffer_request: BufferRequest
    env: dict[str, str] | None = None
    id: TerminalExecutionID = field(default_factory=lambda: str(uuid.uuid4()))
    exit_emitter: EventEmitter[TerminalExecutionExit] = field(default_factory=EventEmitter)

    @property
    def kind(self) -> str:
        return self.driver.kind

    @property
    def on_exit(self) -> Event[TerminalExecutionExit]:
        return self.exit_emitter.event

    def start(self, hooks: TerminalExecutionHooks) -> None:

        def _on_exit(result: Any) -> None:
            result = TerminalExecutionResult(exit_code=result, buffer=self.runner.buffer)
            self.exit_emitter.fire(TerminalExecutionExit(id=self.id, outcome=Success(result)))

        if hooks.on_result:
            self.on_exit.map(lambda exit_entity: exit_entity.outcome).filter(is_success).map(
                lambda success: success.value
            ).once().subscribe(hooks.on_result)

        if hooks.on_exit_code_zero:
            self.on_exit.map(lambda exit_entity: exit_entity.outcome).filter(is_success).map(
                lambda success: success.value
            ).filter(lambda result: result.exit_code == 0).once().subscribe(hooks.on_exit_code_zero)

        if hooks.on_exit_code_non_zero:
            self.on_exit.map(lambda exit_entity: exit_entity.outcome).filter(is_success).map(
                lambda success: success.value
            ).filter(lambda result: result.exit_code != 0).once().subscribe(hooks.on_exit_code_non_zero)

        try:
            job_request = TerminalJobRequest(driver=self.driver, on_exit=_on_exit)
            spawn_option = SpawnOption(cwd=self.cwd, env=self.env)
            self.runner.run(
                job_request, spawn_option
            )  # TODO: Improve the life cycle of `events` of runner and change the order of`subscribe` and `run`.
            self.runner.events.on_job_exit.subscribe(_on_exit)
        except Exception as e:
            self.exit_emitter.fire(TerminalExecutionExit(id=self.id, outcome=Error(exception=e)))


@dataclass(frozen=True)
class TerminalExecutionContext:
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
