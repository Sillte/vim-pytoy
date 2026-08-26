import threading
from functools import wraps
from dataclasses import replace 
from typing import Callable, Self, Sequence
from pathlib import Path

from pytoy.contexts.core import GlobalCoreContext
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.job_execution.environment_manager import EnvironmentManager
from pytoy.job_execution.terminal_executor.manager import TerminalExecutionManager
from pytoy.job_execution.terminal_executor.models import (
    BufferRequest,
    TerminalExecutionRequest,
    TerminalExecution,
    TerminalExecutionContext,
    TerminalExecutionHooks,
    TerminalExecutionID, 
    TerminalExecutionQuery
)
from pytoy.job_execution.terminal_runner import TerminalJobRunner
from pytoy.job_execution.terminal_runner.models import (
    TerminalDriver,
    TerminalDriverProtocol,
    CommandExecutionWrapperType,
)

from pytoy.job_execution.utils import get_current_directory
from .factory import TerminalExecutionFactory 

def assert_main_thread() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError(
            "This method must be called from the main thread."
        )

def main_thread_only[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        assert_main_thread()
        return func(*args, **kwargs)

    return wrapper


class TerminalExecutionHandler:
    def __init__(
        self,
        id: TerminalExecutionID,
        *,
        manager: TerminalExecutionManager,
    ):
        self._id = id
        self._manager = manager

    @classmethod
    def create(cls, request: TerminalExecutionRequest,
                    buffer_request: BufferRequest, *, manager: TerminalExecutionManager | None = None) -> Self:
        if manager is None:
            manager = GlobalPytoyContext.get().terminal_execution_manager
        execution = TerminalExecutionFactory().create(request, buffer_request)
        manager.register(execution)
        return cls(id=execution.id, manager=manager)

    @classmethod
    @main_thread_only
    def query(cls, query: TerminalExecutionQuery, *, manager: TerminalExecutionManager | None = None) -> Sequence[Self]:
        if manager is None:
            manager = GlobalPytoyContext.get().terminal_execution_manager
        executions = manager.select(query=query)
        return [cls(id=item.id, manager=manager) for item in executions]


    @main_thread_only
    def start(
        self,
        hooks: TerminalExecutionHooks | None = None,
    ) -> None:
        hooks = hooks or TerminalExecutionHooks()

        execution = self._manager.get(self._id)

        if execution is None:
            raise ValueError(
                f"`execution` does not exist; {self._id=}"
            )

        execution.start(hooks=hooks)

        context = TerminalExecutionContext(
            buffer_source=execution.buffer_request.source,
            execution_request=replace(
                execution.request,
                cwd=execution.cwd,
                env=execution.env,
            ),
            hooks=hooks,
            kind=execution.kind,
        )

        self._manager.register_context(context)

    @main_thread_only
    def send(self, content: str) -> None:
        execution = self._get_execution()
        execution.runner.send(content)

    @main_thread_only
    def stop(self) -> None:
        execution = self._get_execution()
        execution.runner.interrupt()

    @main_thread_only
    def terminate(self) -> None:
        execution = self._get_execution()
        execution.runner.terminate()


    def _get_execution(self) -> TerminalExecution:
        execution = self._manager.get(self._id)
        if execution is None:
            raise RuntimeError(f"Already `{self._id=}` is terminated.")
        return execution
