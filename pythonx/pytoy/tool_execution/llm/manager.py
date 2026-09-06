from typing import Sequence

from pytoy.tool_execution.llm.models import (
    LLMExecution,
    LLMExecutionContext,
    LLMExecutionID,
    LLMExecutionKind,
    LLMExecutionQuery,
)


class LLMExecutionManager:
    def __init__(self):
        self._executions: dict[LLMExecutionID, LLMExecution] = {}
        self._last_context: LLMExecutionContext | None = None
        self._last_context_by_kind: dict[LLMExecutionKind, LLMExecutionContext] = {}

    def register(self, execution: LLMExecution) -> None:
        self._executions[execution.id] = execution

        def _deregister(_):
            self._executions.pop(execution.id, None)

        execution.on_exit.once().subscribe(_deregister)

    def register_context(self, context: LLMExecutionContext) -> None:
        self._last_context = context
        self._last_context_by_kind[context.kind] = context

    def select(self, query: LLMExecutionQuery | None = None) -> Sequence[LLMExecution]:
        query = query or LLMExecutionQuery()
        target_ids = list(self._executions.keys())
        if query.kind is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].kind == query.kind]
        if query.status is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].task_handler.status == query.status]
        return [self._executions[id_] for id_ in target_ids]

    def get(self, execution_id: LLMExecutionID) -> LLMExecution | None:
        return self._executions.get(execution_id)

    def get_running(self, kind: LLMExecutionKind | None = None) -> Sequence[LLMExecution]:
        query = LLMExecutionQuery(kind=kind, status="running")
        return self.select(query)

    @property
    def last_context(self) -> LLMExecutionContext | None:
        return self._last_context

    def get_last_context_by_kind(self, kind: LLMExecutionKind) -> LLMExecutionContext | None:
        return self._last_context_by_kind.get(kind)
