
from pathlib import Path
from dataclasses import dataclass, field, replace
from typing import Callable, Sequence, Literal, Mapping, Self, Any, assert_never
from pytoy.lib_tools.terminal_runner  import TerminalJobRunner
from pytoy.lib_tools.terminal_runner.models import Snapshot, TerminalJobRequest,  SpawnOption, JobID, Event, JobEvents, TerminalDriverProtocol  
from pytoy.lib_tools.terminal_runner.models import TerminalDriver
from pytoy.ui.pytoy_buffer import PytoyBuffer
import time
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.lib_tools.environment_manager import ExecutionPreference  

CommandWrapper = Callable[[str | list[str] | tuple[str]],  list[str]]

ExecutionWrapperType = CommandWrapper | ExecutionPreference

type ExecutionID = JobID
type ExecutionEvents = JobEvents

type ExecutionName = str


@dataclass(frozen=True)
class BufferRequest:
    stdout: str | PytoyBuffer
    
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
        return BufferRequest(stdout=stdout)


@dataclass(frozen=True)
class ExecutionRequest:
    driver: TerminalDriverProtocol
    command_wrapper: ExecutionWrapperType | None = None
    cwd: str | Path | None = None
    env: dict[str, str] | None = None

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
            
            if not f1: #(f1= None, f2=None), (f1=None, f2=Callable)
                merged_kwargs[item.name] = f2
            elif not f2: #(f1=Callable, f2=None)
                merged_kwargs[item.name] = f1
            else:
                def _merged(f1=f1, f2=f2): 
                    return lambda *a, **k: (f1(*a, **k), f2(*a, **k))
                merged_kwargs[item.name] = _merged()
        return ExecutionHooks(**merged_kwargs)


@dataclass(frozen=True)
class ExecutionContext:
    """ This should be used for repeating the same `Application` again.
    """
    buffer: BufferRequest
    execution_request: ExecutionRequest
    hooks: ExecutionHooks
    name: ExecutionName 


@dataclass(frozen=True)
class TerminalExecution:
    runner: TerminalJobRunner
    driver : TerminalDriverProtocol
    cwd: Path 
    id: ExecutionID
    
    @property
    def events(self) -> ExecutionEvents:
        return self.runner.events

@dataclass(frozen=True)
class ExecutionPolicy:
    buffer_request: BufferRequest
    name: ExecutionName | None = None


class TerminalExecutionManager:
    def __init__(self):
        self._executions: dict[ExecutionID, TerminalExecution] = {}
        self._contexts: dict[ExecutionID, ExecutionContext] = {}
        self._last_context_by_name: dict[ExecutionName, ExecutionContext] = {}
        self._last_context = None

    def register(self, execution: TerminalExecution, context: ExecutionContext):
        self._executions[execution.id] = execution
        self._contexts[execution.id] = context
        self._last_context = context
        self._last_context_by_name[context.name] = context
        def _deregister(_):
            self._executions.pop(execution.id, None)
            self._contexts.pop(execution.id, None)
        execution.events.on_job_exit.subscribe(_deregister)
        
    @property
    def last_context(self) -> ExecutionContext | None:
        return self._last_context
    
    def get_last_context_by_name(self, name: ExecutionName) -> ExecutionContext | None:
        return self._last_context_by_name.get(name)
    
    def get_running(self, name: ExecutionName | None = None) -> list[TerminalExecution]: 
        if not name:
            return list(self._executions.values())
        else:
            return [self._executions[id_] for id_ in self._executions if self._contexts[id_].name == name]

    def running(self) -> list[TerminalExecution]:
        return list(self._executions.values())

    def can_execute(self, policy: ExecutionPolicy) -> bool:
        # Currently, only one `Exceution` is allowed
        # After `Buffer` management syste is introduced, this restriction will become a littel loose.
        # [TODO]: 
        return (not self._executions)
        #  (If)  the required buffer does not have other execuiton, and...
        #return not (any(self._contexts[id_].name == policy.name for id_ in self._executions)) 


class TerminalExecutor:
    def __init__(self, buffer_request: BufferRequest | str, *, ctx: GlobalPytoyContext | None = None):
        if isinstance(buffer_request, str):
            buffer_request = BufferRequest.from_str(buffer_request)
        if ctx is None:
            from pytoy.contexts.pytoy import GlobalPytoyContext
            ctx = GlobalPytoyContext.get()
        self._ctx = ctx
        self._execution_manager: TerminalExecutionManager = ctx.terminal_execution_manager
        self._environment_manager = ctx.core_context.environment_manager
        self._buffer_request = buffer_request
        self._stdout = TerminalJobRunner.solve_buffer(buffer_request.stdout)
        
    @property
    def execution_manager(self) -> TerminalExecutionManager:
        return self._execution_manager

    @property
    def stdout(self) -> PytoyBuffer:
        return self._stdout


    def execute(self, request: ExecutionRequest, hooks: ExecutionHooks | None = None)  -> TerminalExecution:
        if not self.can_execute(request):
            raise ValueError(f"Currently, `{request=}` is not executable.")
        runner = TerminalJobRunner(buffer=self.stdout)

        if hooks is None:
            hooks = ExecutionHooks()
        if not request.cwd:
            # [TODO: Implment `Current` object so that we can get the global state.
            from pytoy.lib_tools.utils import get_current_directory
            cwd = get_current_directory()
        else:
            cwd = Path(request.cwd)
        env = request.env
        driver = self._solve_command_environment(request.driver, request.command_wrapper, cwd=cwd)

        def _on_exit(result: Any, *, hooks: ExecutionHooks) -> None:
            def _call_if_possible(func: Callable[[Any], None] | None):
                if func:
                    func(result)
            _call_if_possible(hooks.on_finish)

        job_request = TerminalJobRequest(driver=driver,
                                        on_exit=lambda result: _on_exit(result, hooks=hooks))
        spawn_option = SpawnOption(cwd=cwd, env=env)
        runner.run(job_request, spawn_option)
        
        context = ExecutionContext(buffer=self._buffer_request.to_str_request(), name=driver.name, 
                                   execution_request=replace(request, cwd=cwd, env=env),
                                   hooks=hooks)
        execution = TerminalExecution(runner=runner, driver=driver, cwd=cwd, id=runner.job_id)

        self._execution_manager.register(execution, context)
        if hooks.on_start:
            hooks.on_start(execution)

        return execution
    
    def can_execute(self, request: ExecutionRequest) -> bool:
        name = request.driver.name
        policy = ExecutionPolicy(buffer_request=self._buffer_request, name=name)
        return self._execution_manager.can_execute(policy)
        
    def _solve_command_environment(self, driver: TerminalDriverProtocol, command_wrapper:  ExecutionWrapperType | None, cwd: str | Path) -> TerminalDriverProtocol:
        if callable(command_wrapper):
            return  TerminalDriver.with_command_wrapper(driver, command_wrapper=command_wrapper)
        else:
            execution_env =  self._environment_manager.solve_preference(cwd, preference=command_wrapper)
            command_wrapper = execution_env.command_wrapper
            return TerminalDriver.with_command_wrapper(driver, command_wrapper)


if __name__ == "__main__":
    pass
