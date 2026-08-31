from pathlib import Path

from pytoy.contexts.core import GlobalCoreContext
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.tool_execution.environment_manager.current import get_current_directory
from pytoy.tool_execution.environment_manager.manager import EnvironmentManager
from pytoy.tool_execution.terminal.contract.models import (
    CommandWrapperType,
    TerminalDriver,
    TerminalDriverProtocol,
)
from pytoy.tool_execution.terminal.infra import (
    SpawnOption,
    TerminalDriverManager,
    TerminalJobRequest,
    TerminalJobRunner,
)

from .models import (
    BufferRequest,
    TerminalDriverKind,
    TerminalExecution,
    TerminalExecutionRequest,
)


class TerminalExecutionFactory:
    def __init__(
        self,
        *,
        environment_manager: EnvironmentManager | None = None,
        driver_manager: TerminalDriverManager | None = None,
    ) -> None:
        if environment_manager is None:
            environment_manager = GlobalCoreContext.get().environment_manager
        if driver_manager is None:
            driver_manager = GlobalPytoyContext.get().terminal_driver_manager
        self._environment_manager = environment_manager
        self._driver_manager = driver_manager

    def create(
        self,
        request: TerminalExecutionRequest,
        buffer_request: BufferRequest,
    ) -> TerminalExecution:
        stdout = TerminalJobRunner.solve_buffer(buffer_request.source)

        if request.cwd is None:
            cwd = get_current_directory()
        else:
            cwd = Path(request.cwd)

        driver = self._resolve_driver_protocol(request.driver)
        driver = self._resolve_command_environment(
            driver=driver,
            command_wrapper=request.command_wrapper,
            cwd=cwd,
        )

        job_request = TerminalJobRequest(driver=driver)
        spawn_option = SpawnOption(cwd=cwd, env=request.env)
        runner = TerminalJobRunner(buffer=stdout, request=job_request, spawn_option=spawn_option)
        execution = TerminalExecution(
            request=request, buffer_request=buffer_request, runner=runner, driver=driver, cwd=cwd, env=request.env
        )
        return execution

    def _resolve_driver_protocol(self, driver: TerminalDriverKind | TerminalDriverProtocol) -> TerminalDriverProtocol:
        if isinstance(driver, TerminalDriverProtocol):
            return driver
        return self._driver_manager.create(driver)

    def _resolve_command_environment(
        self,
        driver: TerminalDriverProtocol,
        command_wrapper: CommandWrapperType | None,
        *,
        cwd: Path,
    ) -> TerminalDriverProtocol:
        if callable(command_wrapper):
            return TerminalDriver.with_command_wrapper(
                driver,
                command_wrapper=command_wrapper,
            )

        execution_env = self._environment_manager.solve_preference(
            cwd,
            preference=command_wrapper,
        )

        return TerminalDriver.with_command_wrapper(
            driver,
            execution_env.command_wrapper,
        )
