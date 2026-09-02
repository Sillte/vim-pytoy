from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Self

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.outcome import Error, Outcome, Success, is_error, is_success
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer
from pytoy.tool_execution.execution_environment import CommandWrapperTypeLike

from .infra import CommandRunner
from .infra.contract import JobEvents, JobID
from .infra.models import JobResult, OutputJobRequest, SpawnOption

type CommandExecutionID = JobID
type CommandExecutionEvents = JobEvents

type CommandExecutionKind = str

type CommandExecutionStatus = Literal["created", "running", "finished", "error"]


@dataclass(frozen=True)
class CommandExecutionResult:
    id: CommandExecutionID
    status: int
    stdout: str  # Snapshot
    stderr: str  # Snapshot
    cwd: Path
    stdout_buffer: PytoyBuffer
    stderr_buffer: PytoyBuffer | None

    def success(self) -> bool:
        return self.status == 0

    @property
    def exit_code(self) -> int:
        return self.status


@dataclass(frozen=True)
class BufferRequest:
    stdout: BufferSource
    stderr: BufferSource | None = None

    @classmethod
    def from_str(cls, stdout: str) -> Self:
        return cls(stdout=BufferSource.from_str(stdout))

    @classmethod
    def from_buffer(cls, buffer: PytoyBuffer) -> Self:
        return cls(stdout=buffer.source)


@dataclass(frozen=True)
class CommandExecutionRequest:
    command: str | list[str]
    cwd: Path | None = None
    command_wrapper: CommandWrapperTypeLike | None = None
    env: Mapping[str, str] | None = None
    kind: CommandExecutionKind = "$default"
    meta: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(
        cls,
        command: str | list[str],
        cwd: str | Path | None = None,
        command_wrapper: CommandWrapperTypeLike | None = None,
        env: Mapping[str, str] | None = None,
        kind: CommandExecutionKind = "$default",
        meta: Mapping[str, Any] | None = None,
    ) -> Self:
        return cls(
            command=command,
            cwd=Path(cwd) if cwd is not None else None,
            command_wrapper=command_wrapper,
            env=env,
            kind=kind,
            meta=meta or {},
        )


@dataclass(frozen=True)
class CommandExecutionResolvedParam:
    stdout_buffer: PytoyBuffer
    stderr_buffer: PytoyBuffer | None
    command: str
    cwd: Path
    env: Mapping[str, Any] | None


@dataclass(frozen=True)
class CommandExecutionHooks:
    """Recommendation policy... Use `on_finish` rather than on_success / on_failure."""

    on_start: Callable[[CommandExecutionResolvedParam], None] | None = None

    on_result: Callable[[CommandExecutionResult], None] | None = None
    on_exception: Callable[[Exception], None] | None = None
    on_exit_code_zero: Callable[[CommandExecutionResult], None] | None = None
    on_exit_code_non_zero: Callable[[CommandExecutionResult], None] | None = None

    @staticmethod
    def merge(hook1: "CommandExecutionHooks", hook2: "CommandExecutionHooks") -> "CommandExecutionHooks":
        from dataclasses import fields

        merged_kwargs = {}
        for item in fields(CommandExecutionHooks):
            f1 = getattr(hook1, item.name)
            f2 = getattr(hook2, item.name)

            if not f1:  # (f1= None, f2=None), (f1=None, f2=Callable)
                merged_kwargs[item.name] = f2
            elif not f2:  # (f1=Callable, f2=None)
                merged_kwargs[item.name] = f1
            else:

                def _merged(f1=f1, f2=f2):  # デフォルト引数でクロージャの参照を固定
                    return lambda *a, **k: (f1(*a, **k), f2(*a, **k))

                merged_kwargs[item.name] = _merged()
        return CommandExecutionHooks(**merged_kwargs)

    @classmethod
    def from_any(
        cls,
        *,
        on_exit_code_zero: Callable[[CommandExecutionResult], None] | None = None,
        on_exit_code_non_zero: Callable[[CommandExecutionResult], None] | None = None,
        on_result: Callable[[CommandExecutionResult], None] | None = None,
        on_exception: Callable[[Exception], None] | None = None,
        on_start: Callable[[CommandExecutionResolvedParam], None] | None = None,
    ) -> Self:
        return cls(
            on_exit_code_zero=on_exit_code_zero,
            on_exit_code_non_zero=on_exit_code_non_zero,
            on_result=on_result,
            on_exception=on_exception,
            on_start=on_start,
        )


@dataclass(frozen=True)
class CommandExecutionExit:
    outcome: Outcome[CommandExecutionResult, Exception]
    id: CommandExecutionID


@dataclass
class CommandExecution:
    runner: CommandRunner
    command: list[str] | str
    cwd: Path
    buffer_request: BufferRequest
    execution_request: CommandExecutionRequest
    env: Mapping[str, str] | None = None
    kind: CommandExecutionKind = "$default"
    status: CommandExecutionStatus | None = "created"
    id: CommandExecutionID = field(default_factory=lambda: str(uuid.uuid4()))
    exit_emitter: EventEmitter[CommandExecutionExit] = field(default_factory=EventEmitter)

    @property
    def events(self) -> CommandExecutionEvents:
        return self.runner.events

    @property
    def on_exit(self) -> Event:
        return self.exit_emitter.event

    @property
    def stdout(self) -> PytoyBuffer:
        return self.runner.stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self.runner.stderr

    def start(self, hooks: CommandExecutionHooks) -> None:
        self.status = "running"

        def _on_exit(job_result: JobResult) -> None:
            self.status = "finished"
            result = CommandExecutionResult(
                id=self.id,
                status=job_result.status,
                stdout=job_result.stdout,
                stdout_buffer=self.stdout,
                stderr=job_result.stderr,
                stderr_buffer=self.stderr,
                cwd=self.cwd,
            )

            exit_entity = CommandExecutionExit(id=self.id, outcome=Success(result))
            self.exit_emitter.fire(exit_entity)

        if hooks.on_exit_code_zero:
            self.exit_emitter.event.map(lambda exit_entity: exit_entity.outcome).filter(is_success).map(
                lambda outcome: outcome.value
            ).filter(lambda result: result.exit_code == 0).once().subscribe(hooks.on_exit_code_zero)

        if hooks.on_exit_code_non_zero:
            self.exit_emitter.event.map(lambda exit_entity: exit_entity.outcome).filter(is_success).map(
                lambda outcome: outcome.value
            ).filter(lambda result: result.exit_code != 0).once().subscribe(hooks.on_exit_code_non_zero)

        if hooks.on_result:
            self.exit_emitter.event.map(lambda exit_entity: exit_entity.outcome).filter(is_success).map(
                lambda outcome: outcome.value
            ).once().subscribe(hooks.on_result)

        if hooks.on_exception:
            self.exit_emitter.event.map(lambda exit_entity: exit_entity.outcome).filter(is_error).map(
                lambda outcome: outcome.exception
            ).once().subscribe(hooks.on_exception)

        job_request = OutputJobRequest(command=self.command, on_exit=lambda job_result: _on_exit(job_result))
        spawn_option = SpawnOption(cwd=self.cwd, env=self.env)
        try:
            self.runner.run(job_request, spawn_option)
        except Exception as exception:
            self.status = "error"
            self.exit_emitter.fire(CommandExecutionExit(id=self.id, outcome=Error(exception)))
            raise

        if hooks.on_start:
            resolved_param = CommandExecutionResolvedParam(
                stdout_buffer=self.stdout,
                stderr_buffer=self.stderr,
                command=self.command if isinstance(self.command, str) else " ".join(self.command),
                cwd=self.cwd,
                env=self.env,
            )
            hooks.on_start(resolved_param)

    def terminate(self) -> None:
        self.runner.terminate()


@dataclass(frozen=True)
class CommandExecutionContext:
    """This should be used for repeating the same `Command`again."""

    buffer: BufferRequest
    execution_request: CommandExecutionRequest
    hooks: CommandExecutionHooks
    kind: CommandExecutionKind = "$default"

    @property
    def meta(self) -> Mapping[str, Any]:
        return self.execution_request.meta


@dataclass(frozen=True)
class CommandExecutionQuery:
    kind: CommandExecutionKind | None = None
    status: CommandExecutionStatus | None = None
    stdout: BufferSource | None = None
