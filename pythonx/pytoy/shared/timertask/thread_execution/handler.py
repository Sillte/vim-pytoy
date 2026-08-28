from __future__ import annotations
import threading
from collections.abc import Callable
from functools import wraps
from typing import Self, Sequence

from pytoy.shared.lib.event import Event
from pytoy.shared.lib.outcome import is_success, is_error
from pytoy.contexts.core import GlobalCoreContext
from .models import (
    ThreadExecutionID,
    ThreadExecutionStatus,
    ThreadExecutionRequest,
    ThreadExecutionHooks,
    ThreadExecutionQuery,
    ThreadExecutionExit,
)
from .manager import ThreadExecutionManager
from .factory import ThreadExecutionFactory


def assert_main_thread() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("This method must be called from the main thread.")


def main_thread_only[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        assert_main_thread()
        return func(*args, **kwargs)

    return wrapper


class ThreadExecutionHandler[T]:
    def __init__(self, id: ThreadExecutionID, manager: ThreadExecutionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    @main_thread_only
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

    @main_thread_only
    def start(self, hooks: ThreadExecutionHooks[T] | None = None) -> None:
        hooks = hooks or ThreadExecutionHooks.from_any()
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")

        execution.on_exit.map(lambda exit: exit.outcome).filter(is_success).map(
            lambda success: success.value
        ).once().subscribe(hooks.on_finish)
        execution.on_exit.map(lambda exit: exit.outcome).filter(is_error).map(
            lambda error: error.exception
        ).once().subscribe(hooks.on_exception)

        execution.start()

    # This is a collaborative cancel, so it can be called from non-main thread.
    def cancel(self) -> None:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        execution.cancel_token.set()

    @property
    def id(self) -> ThreadExecutionID:
        return self._id

    @property
    def status(self) -> ThreadExecutionStatus | None:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            return None
        return execution.status

    @property
    def on_exit(self) -> Event[ThreadExecutionExit[T]]:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        return execution.on_exit
