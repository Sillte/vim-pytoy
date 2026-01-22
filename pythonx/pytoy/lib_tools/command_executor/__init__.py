from pathlib import Path
from dataclasses import dataclass, field, replace
from typing import Callable, Sequence, Literal, Mapping, Self, Any, assert_never
from pytoy.lib_tools.command_runner import CommandRunner
from pytoy.lib_tools.command_runner.models import Snapshot, OutputJobRequest, JobResult, SpawnOption, JobID, Event, JobEvents
from pytoy.ui.pytoy_buffer import PytoyBuffer
import time
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.lib_tools.environment_manager import ExecutionPreference, CommandWrapperType, ExecutionWrapperType  


type ExecutionResult = JobResult
type ExecutionID = JobID
type ExecutionEvents = JobEvents

type ExecutionKind = str


@dataclass(frozen=True)
class BufferRequest:
    stdout: str | PytoyBuffer
    stderr: str | PytoyBuffer | None = None
    
    @classmethod
    def from_str(cls, stdout: str) -> Self:
        return cls(stdout=stdout)

    def to_str_request(self) -> "BufferRequest":
        def _to_name(buffer: PytoyBuffer | str) -> str:
            if isinstance(buffer, PytoyBuffer):
                #[TODO]: This is crucial...May be this should be revised. 
                return Path(buffer.path).name
            return buffer
        stdout = _to_name(self.stdout)
        stderr = _to_name(self.stderr) if self.stderr else None
        return BufferRequest(stdout=stdout, stderr=stderr)

@dataclass(frozen=True)
class ExecutionRequest:
    command: str | list[str] | tuple[str]
    cwd: str | Path | None = None
    command_wrapper: ExecutionWrapperType | None = None
    env: Mapping[str, str] | None = None

@dataclass(frozen=True)
class ExecutionHooks:
    """Recommendation policy... Use `on_finish` rather than on_success / on_failure.
    """
    on_success: Callable[[ExecutionResult], None] | None = None
    on_failure: Callable[[ExecutionResult], None] | None = None
    on_finish: Callable[[ExecutionResult], None] | None = None
    on_start: Callable[["CommandExecution"], None] | None = None
    
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


@dataclass(frozen=True)
class CommandExecution:
    runner: CommandRunner
    command: list[str] | str
    cwd: Path 
    id: ExecutionID
    
    @property
    def events(self) -> ExecutionEvents:
        return self.runner.events

@dataclass(frozen=True)
class ExecutionPolicy:
    kind: ExecutionKind | None = None
    allow_parallel: bool = False
    



class CommandExecutionManager:
    def __init__(self):
        self._executions: dict[ExecutionID, CommandExecution] = {}
        self._contexts: dict[ExecutionID, ExecutionContext] = {}
        self._last_context_by_kind: dict[ExecutionKind, ExecutionContext] = {}
        self._last_context = None

    def register(self, execution: CommandExecution, context: ExecutionContext):
        self._executions[execution.id] = execution
        self._contexts[execution.id] = context
        self._last_context = context
        self._last_context_by_kind[context.kind] = context
        def _deregister(_):
            self._executions.pop(execution.id, None)
            self._contexts.pop(execution.id, None)
        execution.events.on_job_exit.subscribe(_deregister)
        
    @property
    def last_context(self) -> ExecutionContext | None:
        return self._last_context
    
    def get_last_context_by_kind(self, kind: ExecutionKind) -> ExecutionContext | None:
        return self._last_context_by_kind.get(kind)
    
    def get_running(self, kind: ExecutionKind | None = None) -> list[CommandExecution]: 
        if not kind:
            return list(self._executions.values())
        else:
            return [self._executions[id_] for id_ in self._executions if self._contexts[id_].kind == kind]

    def running(self) -> list[CommandExecution]:
        return list(self._executions.values())

    def can_execute(self, policy: ExecutionPolicy) -> bool:
        if policy.allow_parallel:
            return True
        if policy.kind is None:
            return (not self._executions)
        return not (any(self._contexts[id_].kind == policy.kind for id_ in self._executions)) 


class CommandExecutor:
    def __init__(self, buffer_request: BufferRequest | str, *, ctx: GlobalPytoyContext | None = None):
        if isinstance(buffer_request, str):
            buffer_request = BufferRequest.from_str(buffer_request)
        # Once implementation is ended.
        if ctx is None:
            from pytoy.contexts.pytoy import GlobalPytoyContext
            ctx = GlobalPytoyContext.get()
        self._ctx = ctx
        self._execution_manager: CommandExecutionManager = ctx.command_execution_manager
        self._environment_manager = ctx.core_context.environment_manager
        self._buffer_request = buffer_request
        self._stdout, self._stderr = CommandRunner.solve_buffers(buffer_request.stdout, buffer_request.stderr)
        
    @property
    def execution_manager(self) -> CommandExecutionManager:
        return self._execution_manager

    @property
    def stdout(self) -> PytoyBuffer:
        return self._stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self._stderr

    def execute(self, request: ExecutionRequest, hooks: ExecutionHooks | None = None, *,
                 init_buffer: bool = True, kind: ExecutionKind = "$default")  -> CommandExecution:
        runner = CommandRunner(stdout=self.stdout,
                               stderr=self.stderr, init_buffer=init_buffer)
        if hooks is None:
            hooks = ExecutionHooks()
        if not request.cwd:
            # [TODO: Implment `Current` object so that we can get the global state.]
            from pytoy.lib_tools.utils import get_current_directory
            cwd = get_current_directory()
        else:
            cwd = Path(request.cwd)
        env = request.env
        command = self._solve_command(request.command, request.command_wrapper, cwd=cwd)

        def _on_exit(result: ExecutionResult, *, hooks: ExecutionHooks) -> None:
            def _call_if_possible(func: Callable[[ExecutionResult], None] | None):
                if func:
                    func(result)
            if result.success:
                _call_if_possible(hooks.on_success)
            else:
                _call_if_possible(hooks.on_failure)
            _call_if_possible(hooks.on_finish)

        job_request = OutputJobRequest(command=command,
                                        on_exit=lambda result: _on_exit(result, hooks=hooks))
        spawn_option = SpawnOption(cwd=cwd, env=env)


        runner.run(job_request, spawn_option)
        
        
        context = ExecutionContext(buffer=self._buffer_request.to_str_request(),
                                   execution_request=replace(request, cwd=cwd, env=env),
                                   hooks=hooks, kind=kind)
        execution = CommandExecution(runner=runner, command=command, cwd=cwd, id=runner.job_id)

        self._execution_manager.register(execution, context)
        if hooks.on_start:
            hooks.on_start(execution)

        return execution
        
    def _solve_command(self, command: str | list[str] | tuple[str], command_wrapper:  ExecutionWrapperType | None, cwd: str | Path) -> list[str] | str:
        if callable(command_wrapper):
            return command_wrapper(command)
        
        execution_env =  self._environment_manager.solve_preference(cwd, preference=command_wrapper)
        command_wrapper = execution_env.command_wrapper
        return command_wrapper(command)
    
    def can_execute(self, _: ExecutionRequest, kind: ExecutionKind | None = None) -> bool:
        policy = ExecutionPolicy(kind=kind)
        return self._execution_manager.can_execute(policy)


from pytoy.lib_tools.command_executor.quickfix_executor import QuickfixCommandExecutor, QuickfixCommandRequest  # NOQA 


if __name__ == "__main__":
    executor = CommandExecutor("Pytoy:stdout")

    req = ExecutionRequest(
        command=["python", "-c", "print('hello world')"]
    )

    executor.execute(req, hooks=ExecutionHooks())
    
