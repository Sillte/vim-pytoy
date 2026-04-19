#  Models used for `command_executor` package.
# It is intended to behaive like a domain model in this package.

from pathlib import Path
from dataclasses import dataclass, field
from pytoy.job_execution.command_runner import CommandRunner
from typing import Callable, Mapping, Self, Any
from pytoy.job_execution.command_runner.models import JobResult, JobID, JobEvents
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer, BufferSource
from pytoy.job_execution.environment_manager import  ExecutionWrapperType  


type ExecutionResult = JobResult
type ExecutionID = JobID
type ExecutionEvents = JobEvents

type ExecutionKind = str



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
class ExecutionRequest:
    command: str | list[str] | tuple[str]
    cwd: str | Path | None = None
    command_wrapper: ExecutionWrapperType | None = None
    env: Mapping[str, str] | None = None
    kind: ExecutionKind = "$default"
    meta: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandExecution:
    runner: CommandRunner
    command: list[str] | str
    cwd: Path 
    id: ExecutionID
    
    @property
    def events(self) -> ExecutionEvents:
        return self.runner.events

    @property
    def stdout(self) -> PytoyBuffer:
        return self.runner.stdout
    


@dataclass(frozen=True)
class PostProcessContext:
    result: ExecutionResult
    execution: CommandExecution
    
    @property
    def stdout(self) -> PytoyBuffer:
        return self.execution.runner.stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self.execution.runner.stderr


@dataclass(frozen=True)
class ExecutionHooks:
    """Recommendation policy... Use `on_finish` rather than on_success / on_failure.
    """
    on_success: Callable[[ExecutionResult], None] | None = None
    on_failure: Callable[[ExecutionResult], None] | None = None
    on_finish: Callable[[ExecutionResult], None] | None = None
    on_start: Callable[[CommandExecution], None] | None = None
    on_post_process: Callable[[PostProcessContext], None] | None = None
    
    @staticmethod
    def merge(hook1: "ExecutionHooks", hook2: "ExecutionHooks") -> "ExecutionHooks":
        from dataclasses import fields
        
        merged_kwargs = {}
        for item in fields(ExecutionHooks):
            f1 = getattr(hook1, item.name)
            f2 = getattr(hook2, item.name)
            
            if not f1: #(f1= None, f2=None), (f1=None, f2=Callable)
                merged_kwargs[item.name] = f2
            elif not f2: #(f1=Callable, f2=None)
                merged_kwargs[item.name] = f1
            else:
                def _merged(f1=f1, f2=f2): # デフォルト引数でクロージャの参照を固定
                    return lambda *a, **k: (f1(*a, **k), f2(*a, **k))
                merged_kwargs[item.name] = _merged()
        return ExecutionHooks(**merged_kwargs)


@dataclass(frozen=True)
class ExecutionContext:
    """ This should be used for repeating the same `Command`again.
    """
    buffer: BufferRequest
    execution_request: ExecutionRequest
    hooks: ExecutionHooks
    kind: ExecutionKind = "$default"
    
    @property
    def meta(self) -> Mapping[str, Any]:
        return self.execution_request.meta


@dataclass(frozen=True)
class ExecutionPolicy:
    kind: ExecutionKind | None = None
    allow_parallel: bool = False
    
@dataclass(frozen=True)
class ExecutionQuery:
    kind: ExecutionKind | None  = None
    stdout: BufferSource | None = None

