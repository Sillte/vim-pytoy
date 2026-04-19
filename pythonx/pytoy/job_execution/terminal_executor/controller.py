from dataclasses import dataclass
from pathlib import Path

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.job_execution.terminal_executor.executor import TerminalExecutionManager, TerminalExecutor
from pytoy.job_execution.terminal_executor.models import BufferRequest, DriverKind, ExecutionRequest, TerminalDriverProtocol, TerminalExecution, ExecutionWrapperType
from pytoy.job_execution.terminal_runner.drivers import TerminalDriverManager
from pytoy.shared.ui.pytoy_buffer import BufferSource


@dataclass(frozen=True)
class LaunchProfile:
    command_wrapper: ExecutionWrapperType | None = None
    cwd: Path | None = None


class TerminalController:
    def __init__(self, driver_manager: TerminalDriverManager | None = None, execution_manager: TerminalExecutionManager | None = None):
        ctx = GlobalPytoyContext.get()
        self._driver_manager = driver_manager or ctx.terminal_driver_manager
        self._execution_manager = execution_manager or ctx.terminal_execution_manager

    @property
    def driver_manager(self) -> TerminalDriverManager:
        return self._driver_manager

    @property
    def execution_manager(self) -> TerminalExecutionManager:
        return self._execution_manager

    def _to_driver_kind(self, driver: DriverKind | TerminalDriverProtocol) -> DriverKind:
        return  driver if isinstance(driver, str) else driver.kind


    def send(self,  driver: DriverKind | TerminalDriverProtocol, buffer_name: str | Path | BufferSource, content: str,  *, launch_profile: LaunchProfile | None = None) ->  TerminalExecution:
        launch_profile = launch_profile or LaunchProfile()
        execution = self.get_or_create_execution(driver, buffer_name, launch_profile=launch_profile)
        execution.runner.send(content)
        return execution

    def stop(self, buffer: str | BufferSource | Path):
        buffer_source = BufferSource.from_any(buffer)
        if (executions := self.execution_manager.get_running(kind = None, buffer=buffer_source)):
            execution = executions[0]
            execution.runner.interrupt()
        else:
            print("Target Executor is not existent.")

    def terminate(self, buffer: str | Path | BufferSource) -> None:
        buffer_source = BufferSource.from_any(buffer)
        executions = self.execution_manager.get_running(kind = None, buffer=buffer_source)
        for execution in executions:
            execution.runner.terminate()
        if not executions:
            print("Target Executor is not existent.")


    def get_or_create_execution(
        self, driver: str | TerminalDriverProtocol, buffer_name: str | Path | BufferSource, *, launch_profile: LaunchProfile | None = None,
    ) -> TerminalExecution:
        launch_profile = launch_profile or LaunchProfile()
        driver_kind = self._to_driver_kind(driver)
        buffer_source = BufferSource.from_any(buffer_name)
        executions = self.execution_manager.get_running(kind=driver_kind, buffer=buffer_source)
        if executions:
            execution = executions[0]
        else:
            buffer_req = BufferRequest(source=buffer_source)
            driver = self.driver_manager.create(driver_kind=driver_kind)
            execution_req = ExecutionRequest(driver=driver, command_wrapper=launch_profile.command_wrapper, cwd=launch_profile.cwd)
            executor = TerminalExecutor(buffer_req)
            execution = executor.execute(execution_req)
        return execution