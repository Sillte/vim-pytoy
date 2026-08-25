import threading
from collections.abc import Callable
from functools import wraps
from typing import Self, Sequence

from pytoy.contexts.core import GlobalCoreContext
from. models import  ThreadExecutionID, ThreadExecutionStatus, ThreadExecutionRequest, ThreadExecutionHooks, ThreadExecutionQuery
from .manager import ThreadExecutionManager
from .factory import ThreadExecutionFactory

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


class ThreadExecutionHandler:
    def __init__(self, id: ThreadExecutionID, manager: ThreadExecutionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    @main_thread_only
    def create(cls, request: ThreadExecutionRequest,  *, manager: ThreadExecutionManager | None = None) -> Self:
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
    def start(self, hooks: ThreadExecutionHooks | None = None) -> None:
        hooks = hooks or ThreadExecutionHooks.from_any()
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        execution.start(hooks=hooks)

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



