from threading import RLock
from typing import Callable, Sequence

from pytoy.tool_execution.llm.models import (
    LLMExecution,
    LLMExecutionContext,
    LLMExecutionID,
    LLMExecutionKind,
    LLMExecutionQuery,
)


class LLMExecutionManager:
    def __init__(self):
        self._lock = RLock()
        self._executions: dict[LLMExecutionID, LLMExecution] = {}
        self._last_context: LLMExecutionContext | None = None
        self._last_context_by_kind: dict[LLMExecutionKind, LLMExecutionContext] = {}

    def register(self, execution: LLMExecution) -> None:
        with self._lock:
            self._executions[execution.id] = execution

        def _deregister(_):
            with self._lock:
                self._executions.pop(execution.id, None)

        def _deregister_if_not_running(_):
            if execution.task_handler.status == "canceled":
                _deregister(None)

        execution.on_exit.once().subscribe(_deregister)
        execution.task_handler.on_cancel.once().subscribe(_deregister_if_not_running)

    def cancel_execution(self, execution_id: LLMExecutionID) -> None:
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                raise ValueError(f"`LLMExecution` does not exist; {execution_id=}")
            execution.task_handler.cancel()

    def register_context(self, context: LLMExecutionContext) -> None:
        with self._lock:
            self._last_context = context
            self._last_context_by_kind[context.kind] = context

    def start_execution[T](self, execution_id: LLMExecutionID, start: Callable[[LLMExecution[T]], None]) -> None:
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                raise ValueError(f"`LLMExecution` does not exist; {execution_id=}")
            if execution.task_handler.status != "created":
                raise RuntimeError("Only a created LLM execution can be started.")
            start(execution)

    def select(self, query: LLMExecutionQuery | None = None) -> Sequence[LLMExecution]:
        query = query or LLMExecutionQuery()
        with self._lock:
            executions = tuple(self._executions.values())
            if query.kind is not None:
                executions = tuple(item for item in executions if item.kind == query.kind)
            if query.status is not None:
                executions = tuple(item for item in executions if item.task_handler.status == query.status)
            return executions

    def get(self, execution_id: LLMExecutionID) -> LLMExecution | None:
        with self._lock:
            return self._executions.get(execution_id)

    def get_running(self, kind: LLMExecutionKind | None = None) -> Sequence[LLMExecution]:
        query = LLMExecutionQuery(kind=kind, status="running")
        return self.select(query)

    @property
    def last_context(self) -> LLMExecutionContext | None:
        with self._lock:
            return self._last_context

    def get_last_context_by_kind(self, kind: LLMExecutionKind) -> LLMExecutionContext | None:
        with self._lock:
            return self._last_context_by_kind.get(kind)
