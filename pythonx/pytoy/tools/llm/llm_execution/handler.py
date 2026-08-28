import threading
from collections.abc import Callable
from functools import wraps
from typing import Self, Sequence

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.event import Event
from pytoy.shared.lib.outcome import is_error, is_success

from .factory import LLMExecutionFactory
from .manager import LLMExecutionManager
from .models import (
    LLMExecutionContext,
    LLMExecutionExit,
    LLMExecutionHooks,
    LLMExecutionID,
    LLMExecutionQuery,
    LLMExecutionRequest,
    LLMExecutionStatus,
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


class LLMExecutionHandler[T]:
    def __init__(self, id: LLMExecutionID, *, manager: LLMExecutionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    @main_thread_only
    def create(cls, request: LLMExecutionRequest, *, manager: LLMExecutionManager | None = None) -> Self:
        if manager is None:
            manager = GlobalPytoyContext.get().llm_execution_manager
        factory = LLMExecutionFactory()
        execution = factory.create(request)
        manager.register(execution)
        return cls(id=execution.id, manager=manager)

    @classmethod
    def query(
        cls, query: LLMExecutionQuery | None = None, *, manager: LLMExecutionManager | None = None
    ) -> Sequence[Self]:
        query = query or LLMExecutionQuery()
        if manager is None:
            manager = GlobalPytoyContext.get().llm_execution_manager
        executions = manager.select(query)
        return [cls(id=execution.id, manager=manager) for execution in executions]

    @property
    def status(self) -> LLMExecutionStatus | None:
        execution = self._manager.get(self._id)
        if execution is None:
            return None
        return execution.status

    @main_thread_only
    def start(self, hooks: LLMExecutionHooks | None = None) -> None:
        hooks = hooks or LLMExecutionHooks.from_any()
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")

        execution.start(hooks=hooks)

        context = LLMExecutionContext(
            request=execution.request,
            hooks=hooks,
        )

        self.on_exit.map(lambda exit_entity: exit_entity.outcome).filter(is_success).map(
            lambda success: success.value
        ).once().subscribe(hooks.on_finish)
        self.on_exit.map(lambda exit_entity: exit_entity.outcome).filter(is_error).map(
            lambda error: error.exception
        ).once().subscribe(hooks.on_exception)
        self._manager.register_context(execution, context)

    @property
    def id(self) -> LLMExecutionID:
        return self._id

    @property
    def on_exit(self) -> Event[LLMExecutionExit[T]]:
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        return execution.on_exit
