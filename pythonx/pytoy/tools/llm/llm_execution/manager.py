from typing import Sequence

from pytoy.tools.llm.llm_execution.models import (
    ExecutionPolicy,
    LLMExecution,
    LLMExecutionContext,
    LLMExecutionID,
    LLMExecutionKind,
    LLMExecutionQuery,
)


class LLMExecutionManager:
    def __init__(self):
        self._executions: dict[LLMExecutionID, LLMExecution] = {}
        self._contexts: dict[LLMExecutionID, LLMExecutionContext] = {}
        self._last_context: LLMExecutionContext | None = None
        self._last_context_by_kind: dict[LLMExecutionKind, LLMExecutionContext] = {}

    def register(self, execution: LLMExecution) -> None:
        self._executions[execution.id] = execution

        def _deregister(_):
            self._executions.pop(execution.id, None)
            self._contexts.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)

    def register_context(self, execution: LLMExecution, context: LLMExecutionContext) -> None:
        self._contexts[execution.id] = context

        self._last_context = context
        self._last_context_by_kind[context.kind] = context

    def select(self, query: LLMExecutionQuery | None = None) -> Sequence[LLMExecution]:
        query = query or LLMExecutionQuery()
        target_ids = list(self._executions.keys())
        if query.kind is not None:
            target_ids = [id_ for id_ in target_ids if self._contexts[id_].kind == query.kind]
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

    def can_execute(self, policy: ExecutionPolicy) -> bool:
        if policy.allow_parallel:
            return True
        if policy.kind is None:
            return not self._executions
        return not (any(self._contexts[id_].kind == policy.kind for id_ in self._executions))
