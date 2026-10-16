import logging
from concurrent.futures import Future, InvalidStateError
from functools import cached_property
from typing import Self, Sequence

from pytoy_llm.task.execution import TaskExecutionHandler

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.event import Event
from pytoy.shared.lib.outcome import is_error, is_success
from pytoy.shared.timertask import backend_or_main_thread_only

from .factory import LLMExecutionFactory
from .manager import LLMExecutionManager
from .models import (
    LLMExecution,
    LLMExecutionContext,
    LLMExecutionExit,
    LLMExecutionHooks,
    LLMExecutionID,
    LLMExecutionKind,
    LLMExecutionQuery,
    LLMExecutionRequest,
    LLMExecutionStatus,
)


class LLMExecutionHandler[T]:
    def __init__(self, id: LLMExecutionID, *, manager: LLMExecutionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    @backend_or_main_thread_only
    def create(cls, request: LLMExecutionRequest, *, manager: LLMExecutionManager | None = None) -> Self:
        if manager is None:
            manager = GlobalPytoyContext.get().llm_execution_manager
        factory = LLMExecutionFactory()
        llm_execution = factory.create(request)
        manager.register(llm_execution)
        return cls(id=llm_execution.id, manager=manager)

    @classmethod
    @backend_or_main_thread_only
    def create_from_task_handler(
        cls,
        task_handler: TaskExecutionHandler,
        kind: LLMExecutionKind,
        *,
        logger: logging.Logger | None = None,
        manager: LLMExecutionManager | None = None,
    ) -> Self:
        if manager is None:
            manager = GlobalPytoyContext.get().llm_execution_manager
        if task_handler.status != "created":
            raise ValueError(f"Only `created` task_handler is accepted, but `{task_handler.status=}`")
        factory = LLMExecutionFactory()
        llm_execution = factory.create_from_task_handler(task_handler, kind, logger=logger)
        manager.register(llm_execution)
        return cls(id=llm_execution.id, manager=manager)

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
        return self._require_task_handler().status

    @backend_or_main_thread_only
    def start(self, hooks: LLMExecutionHooks | None = None) -> Future[LLMExecutionExit[T]]:
        hooks = hooks or LLMExecutionHooks.from_any()
        future: Future[LLMExecutionExit[T]] = Future()

        def complete(exit_entity: LLMExecutionExit[T]) -> None:
            try:
                future.set_result(exit_entity)
            except InvalidStateError:
                if not future.cancelled():
                    raise

        def start_execution(execution: LLMExecution[T]) -> None:
            disposables = []
            try:
                disposables.append(self.on_exit.once().subscribe(complete))
                disposables.append(
                    self.on_exit.map(lambda exit_entity: exit_entity.outcome)
                    .filter(is_success)
                    .map(lambda success: success.value)
                    .once()
                    .subscribe(hooks.on_result)
                )
                disposables.append(
                    self.on_exit.map(lambda exit_entity: exit_entity.outcome)
                    .filter(is_error)
                    .map(lambda error: error.exception)
                    .once()
                    .subscribe(hooks.on_exception)
                )
                self._manager.register_context(LLMExecutionContext(kind=execution.kind, hooks=hooks))
                execution.task_handler.start()
            except BaseException:
                for disposable in disposables:
                    disposable.dispose()
                raise

        self._manager.start_execution(self._id, start_execution)
        return future

    @property
    def id(self) -> LLMExecutionID:
        return self._id

    @cached_property
    def on_exit(self) -> Event[LLMExecutionExit[T]]:
        return self._require_execution().exit_emitter.event

    def _require_execution(self) -> LLMExecution[T]:
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`LLMExecution` does not exist; {self._id=}")
        return execution

    def _require_task_handler(self) -> TaskExecutionHandler[T]:
        return self._require_execution().task_handler
