from __future__ import annotations

import threading
from collections.abc import Callable
from functools import wraps
from typing import Self, Sequence

from pytoy.contexts.core import GlobalCoreContext
from pytoy.shared.lib.event import Event
from pytoy.shared.lib.outcome import is_error, is_success
from pytoy.shared.timertask.timertask import TimerTask

from .factory import ThreadExecutionFactory
from .manager import ThreadExecutionManager
from .models import (
    ThreadExecution,
    ThreadExecutionExit,
    ThreadExecutionHooks,
    ThreadExecutionID,
    ThreadExecutionQuery,
    ThreadExecutionRequest,
    ThreadExecutionStatus,
)


def assert_execution_thread() -> None:
    if threading.current_thread() is threading.main_thread() or TimerTask.is_dispatch_thread():
        return
    raise RuntimeError("This method must be called from the main thread or a TimerTask dispatch thread.")


def execution_thread_only[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        assert_execution_thread()
        return func(*args, **kwargs)

    return wrapper


class ThreadExecutionHandler[T]:
    def __init__(self, id: ThreadExecutionID, manager: ThreadExecutionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    @execution_thread_only
    def create(cls, request: ThreadExecutionRequest[T], *, manager: ThreadExecutionManager | None = None) -> Self:
        if manager is None:
            manager = GlobalCoreContext.get().thread_execution_manager
        factory = ThreadExecutionFactory(manager=manager)
        execution = factory.create(request)
        return cls(id=execution.id, manager=manager)

    @classmethod
    def query(cls, query: ThreadExecutionQuery, *, manager: ThreadExecutionManager | None = None) -> Sequence[Self]:
        if manager is None:
            manager = GlobalCoreContext.get().thread_execution_manager
        executions = manager.select(query)
        return [cls(id=execution.id, manager=manager) for execution in executions]

    @execution_thread_only
    def start(self, hooks: ThreadExecutionHooks[T] | None = None) -> None:
        hooks = hooks or ThreadExecutionHooks.from_any()

        def start_execution(execution: ThreadExecution[T]) -> None:
            execution.on_exit.map(lambda exit: exit.outcome).filter(is_success).map(
                lambda success: success.value
            ).once().subscribe(hooks.on_result)
            execution.on_exit.map(lambda exit: exit.outcome).filter(is_error).map(
                lambda error: error.exception
            ).once().subscribe(hooks.on_exception)
            execution.start()

        self._manager.start_execution(self._id, start_execution)

    # This is a collaborative cancel, so it can be called from non-main thread.
    def cancel(self) -> None:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        execution.cancel_token.set()

    @execution_thread_only
    def discard(self) -> None:
        """Remove an execution that has not been started."""
        self._manager.discard_unstarted(self._id)

    @property
    def id(self) -> ThreadExecutionID:
        return self._id

    @property
    def status(self) -> ThreadExecutionStatus | None:
        return self._manager.get_status(self._id)

    @property
    def on_exit(self) -> Event[ThreadExecutionExit[T]]:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        return execution.on_exit
