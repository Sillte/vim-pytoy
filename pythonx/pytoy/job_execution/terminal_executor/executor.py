from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.job_execution.terminal_executor.manager import TerminalExecutionManager
from pytoy.job_execution.terminal_executor.models import (
    BufferRequest,
    ExecutionContext,
    ExecutionHooks,
    ExecutionPolicy,
    ExecutionRequest,
    TerminalExecution,
)
from pytoy.job_execution.terminal_runner import TerminalJobRunner
from pytoy.job_execution.terminal_runner.models import (
    SpawnOption,
    TerminalDriver,
    TerminalDriverProtocol,
    TerminalJobRequest,
    ExecutionWrapperType,
)
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer


from dataclasses import replace
from pathlib import Path
from typing import Any, Callable


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
        self._stdout = TerminalJobRunner.solve_buffer(buffer_request.source)

    @property
    def execution_manager(self) -> TerminalExecutionManager:
        return self._execution_manager

    @property
    def stdout(self) -> PytoyBuffer:
        return self._stdout

    def execute(self, request: ExecutionRequest, hooks: ExecutionHooks | None = None) -> TerminalExecution:
        if not self.can_execute(request):
            raise ValueError(f"Currently, `{request=}` is not executable.")
        runner = TerminalJobRunner(buffer=self.stdout)

        if hooks is None:
            hooks = ExecutionHooks()
        if not request.cwd:
            # [TODO: Implment `Current` object so that we can get the global state.
            from pytoy.job_execution.utils import get_current_directory

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

        job_request = TerminalJobRequest(driver=driver, on_exit=lambda result: _on_exit(result, hooks=hooks))
        spawn_option = SpawnOption(cwd=cwd, env=env)
        runner.run(job_request, spawn_option)

        context = ExecutionContext(
            buffer_source=self._buffer_request.source,
            kind=driver.kind,
            execution_request=replace(request, cwd=cwd, env=env),
            hooks=hooks,
        )
        execution = TerminalExecution(runner=runner, driver=driver, cwd=cwd, id=runner.job_id)

        self._execution_manager.register(execution, context)
        if hooks.on_start:
            hooks.on_start(execution)

        return execution

    def can_execute(self, request: ExecutionRequest) -> bool:
        name = request.driver.kind
        policy = ExecutionPolicy(buffer_request=self._buffer_request, kind=name)
        return self._execution_manager.can_execute(policy)

    def _solve_command_environment(
        self, driver: TerminalDriverProtocol, command_wrapper: ExecutionWrapperType | None, cwd: str | Path
    ) -> TerminalDriverProtocol:
        if callable(command_wrapper):
            return TerminalDriver.with_command_wrapper(driver, command_wrapper=command_wrapper)
        else:
            execution_env = self._environment_manager.solve_preference(cwd, preference=command_wrapper)
            return TerminalDriver.with_command_wrapper(driver, execution_env.command_wrapper)
