import uuid
from pathlib import Path
from threading import Thread

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.contexts.core import GlobalCoreContext
from pytoy.job_execution.environment_manager import EnvironmentManager
from pytoy.job_execution.command_runner import CommandRunner

from threading import Event 
from .models import CommandExecution, CommandExecutionHooks, CommandExecutionRequest, CommandExecutionResult, BufferRequest, CommandExecutionWrapperType
from .manager import CommandExecutionManager

class CommandExecutionFactory:
    def __init__(self, *, manager: CommandExecutionManager | None = None, environment_manager: EnvironmentManager | None = None):
        if manager is None:
            manager = GlobalPytoyContext.get().command_execution_manager
        if environment_manager is None:
            environment_manager = GlobalCoreContext.get().environment_manager 
        self._manager: CommandExecutionManager = manager
        self._environment_manager: EnvironmentManager = environment_manager

    def create(self, request: CommandExecutionRequest, buffer_request: BufferRequest, *, init_buffer: bool = False) -> CommandExecution: 
        stdout, stderr = CommandRunner.solve_buffers(buffer_request.stdout, buffer_request.stderr)
        runner = CommandRunner(stdout=stdout, stderr=stderr, init_buffer=init_buffer)

        if request.cwd is None:
            # [TODO: Implement `Current` object so that we can get the global state.]
            from pytoy.job_execution.utils import get_current_directory
            cwd = get_current_directory()
        else:
            cwd = Path(request.cwd)
        command = self._solve_command(request.command, request.command_wrapper, cwd=cwd)
        env = request.env or {}
        execution = CommandExecution(runner=runner, command=command, buffer_request=buffer_request, execution_request=request, cwd=cwd, env=env, kind=request.kind)
        self._manager.register(execution)
        return execution


    def _solve_command(
        self, command: str | list[str] | tuple[str], command_wrapper: CommandExecutionWrapperType | None, cwd: str | Path
    ) -> list[str] | str:
        if callable(command_wrapper):
            return command_wrapper(command)

        execution_env = self._environment_manager.solve_preference(cwd, preference=command_wrapper)
        command_wrapper = execution_env.command_wrapper
        return command_wrapper(command)