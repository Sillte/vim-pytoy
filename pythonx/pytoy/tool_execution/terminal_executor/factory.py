from pathlib import Path

from pytoy.contexts.core import GlobalCoreContext
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.job_execution.environment_manager import EnvironmentManager
from pytoy.job_execution.terminal_runner import TerminalJobRunner
from pytoy.job_execution.terminal_runner.drivers import TerminalDriverManager
from pytoy.job_execution.terminal_runner.models import (
    CommandExecutionWrapperType,
    TerminalDriver,
    TerminalDriverProtocol,
)
from pytoy.job_execution.utils import get_current_directory
from pytoy.tool_execution.terminal_executor.models import (
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

        runner = TerminalJobRunner(buffer=stdout)

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
        command_wrapper: CommandExecutionWrapperType | None,
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
