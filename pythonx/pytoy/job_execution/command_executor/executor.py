from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.job_execution.command_executor.manager import CommandExecutionManager
from pytoy.job_execution.command_executor.models import (
    BufferRequest,
    CommandExecution,
    CommandExecutionContext,
    CommandExecutionHooks,
    CommandExecutionKind,
    CommandExecutionRequest,
    CommandExecutionResult,
    PostProcessContext,
    CommandExecutionWrapperType,
)
from pytoy.job_execution.command_runner import CommandRunner
from pytoy.job_execution.command_runner.models import OutputJobRequest, SpawnOption
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer

from dataclasses import replace
from pathlib import Path
from typing import Callable


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

    def execute(
        self, request: CommandExecutionRequest, hooks: CommandExecutionHooks | None = None, *, init_buffer: bool = True
    ) -> CommandExecution:
        runner = CommandRunner(stdout=self.stdout, stderr=self.stderr, init_buffer=init_buffer)
        if hooks is None:
            hooks = CommandExecutionHooks()
        if not request.cwd:
            # [TODO: Implment `Current` object so that we can get the global state.]
            from pytoy.job_execution.utils import get_current_directory

            cwd = get_current_directory()
        else:
            cwd = Path(request.cwd)
        env = request.env
        command = self._solve_command(request.command, request.command_wrapper, cwd=cwd)

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
                post_process = PostProcessContext(result=result, execution=execution)
                hooks.on_post_process(post_process)

        job_request = OutputJobRequest(command=command, on_exit=lambda result: _on_exit(result, hooks=hooks))
        spawn_option = SpawnOption(cwd=cwd, env=env)

        runner.run(job_request, spawn_option)

        context = CommandExecutionContext(
            buffer=self._buffer_request,
            execution_request=replace(request, cwd=cwd, env=env),
            hooks=hooks,
            kind=request.kind,
        )
        execution = CommandExecution(runner=runner, command=command, cwd=cwd, id=runner.job_id)

        self._execution_manager.register(execution, context)
        if hooks.on_start:
            hooks.on_start(execution)

        return execution

    def _solve_command(
        self, command: str | list[str] | tuple[str], command_wrapper: CommandExecutionWrapperType | None, cwd: str | Path
    ) -> list[str] | str:
        if callable(command_wrapper):
            return command_wrapper(command)

        execution_env = self._environment_manager.solve_preference(cwd, preference=command_wrapper)
        command_wrapper = execution_env.command_wrapper
        return command_wrapper(command)



if __name__ == "__main__":
    pass
