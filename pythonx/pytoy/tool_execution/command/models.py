from __future__ import annotations

#  Models used for `command_executor` package.
# It is intended to behaive like a domain model in this package.
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Self

from pytoy.job_execution.command_runner import CommandRunner
from pytoy.job_execution.command_runner.models import JobEvents, JobID, JobResult, OutputJobRequest, SpawnOption
from pytoy.job_execution.environment_manager import CommandExecutionWrapperType
from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer

type CommandExecutionResult = JobResult
type CommandExecutionID = JobID
type CommandExecutionEvents = JobEvents

type CommandExecutionKind = str

type CommandExecutionStatus = Literal["created", "running", "finished", "error"]


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
    command_wrapper: CommandExecutionWrapperType | None = None
    env: Mapping[str, str] | None = None
    kind: CommandExecutionKind = "$default"
    meta: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(
        cls,
        command: str | list[str],
        cwd: str | Path | None = None,
        command_wrapper: CommandExecutionWrapperType | None = None,
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
class CommandExecutionHooks:
    """Recommendation policy... Use `on_finish` rather than on_success / on_failure."""

    on_success: Callable[[CommandExecutionResult], None] | None = None
    on_failure: Callable[[CommandExecutionResult], None] | None = None
    on_finish: Callable[[CommandExecutionResult], None] | None = None
    on_start: Callable[["CommandExecution"], None] | None = None
    on_post_process: Callable[["PostProcessContext"], None] | None = None

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
        on_success: Callable[[CommandExecutionResult], None] | None = None,
        on_failure: Callable[[CommandExecutionResult], None] | None = None,
        on_finish: Callable[[CommandExecutionResult], None] | None = None,
        on_start: Callable[["CommandExecution"], None] | None = None,
        on_post_process: Callable[["PostProcessContext"], None] | None = None,
    ) -> Self:
        return cls(
            on_success=on_success,
            on_failure=on_failure,
            on_finish=on_finish,
            on_start=on_start,
            on_post_process=on_post_process,
        )


@dataclass
class CommandExecution:
    runner: CommandRunner
    command: list[str] | str
    cwd: Path
    buffer_request: BufferRequest
    execution_request: CommandExecutionRequest
    env: Mapping[str, str] = field(default_factory=dict)
    kind: CommandExecutionKind = "$default"
    status: CommandExecutionStatus | None = "created"
    id: CommandExecutionID = field(default_factory=lambda: str(uuid.uuid4()))
    exit_emitter: EventEmitter[None] = field(default_factory=EventEmitter)

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

        def _on_exit(result: CommandExecutionResult, *, hooks: CommandExecutionHooks) -> None:
            def _call_if_possible(func: Callable[[CommandExecutionResult], None] | None):
                if func:
                    func(result)

            if result.success:
                _call_if_possible(hooks.on_success)
            else:
                _call_if_possible(hooks.on_failure)
            _call_if_possible(hooks.on_finish)

            if hooks.on_post_process:
                post_process = PostProcessContext(result=result, execution=self)
                hooks.on_post_process(post_process)

        job_request = OutputJobRequest(command=self.command, on_exit=lambda result: _on_exit(result, hooks=hooks))
        spawn_option = SpawnOption(cwd=self.cwd, env=self.env)
        self.runner.run(job_request, spawn_option)

        self.runner.events.on_job_exit.subscribe(lambda _: self.exit_emitter.fire(None))

        if hooks.on_start:
            hooks.on_start(self)

    def terminate(self) -> None:
        self.runner.terminate()


@dataclass(frozen=True)
class PostProcessContext:
    result: CommandExecutionResult
    execution: CommandExecution

    @property
    def stdout(self) -> PytoyBuffer:
        return self.execution.runner.stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self.execution.runner.stderr


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
    stdout: BufferSource | None = None
