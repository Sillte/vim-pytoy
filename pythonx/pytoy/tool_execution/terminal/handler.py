import threading
from dataclasses import replace
from functools import wraps
from typing import Callable, Self, Sequence

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.event import Event

from .factory import TerminalExecutionFactory
from .manager import TerminalExecutionManager
from .models import (
    BufferRequest,
    TerminalExecution,
    TerminalExecutionContext,
    TerminalExecutionExit,
    TerminalExecutionHooks,
    TerminalExecutionID,
    TerminalExecutionQuery,
    TerminalExecutionRequest,
    TerminalExecutionStatus,
)


def assert_main_thread() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("This method must be called from the main thread.")


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
    @main_thread_only
    def create(
        cls,
        request: TerminalExecutionRequest,
        buffer_request: BufferRequest,
        *,
        manager: TerminalExecutionManager | None = None,
    ) -> Self:
        if manager is None:
            manager = GlobalPytoyContext.get().terminal_execution_manager
        execution = TerminalExecutionFactory().create(request, buffer_request)
        manager.register(execution)
        return cls(id=execution.id, manager=manager)

    @classmethod
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
            raise ValueError(f"`execution` does not exist; {self._id=}")

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

    @property
    def status(self) -> TerminalExecutionStatus:
        execution = self._get_execution()
        return execution.status

    @property
    def on_exit(self) -> Event[TerminalExecutionExit]:
        execution = self._get_execution()
        return execution.on_exit

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
