from pytoy.tools.llm.llm_execution.models import (
    ExecutionID,
    ExecutionKind,
    LLMExecution,
    ExecutionContext,
    ExecutionQuery,
    ExecutionPolicy,
)
from typing import Sequence


class LLMExecutionManager:
    def __init__(self):
        self._executions: dict[ExecutionID, LLMExecution] = {}
        self._contexts: dict[ExecutionID, ExecutionContext] = {}
        self._last_context: ExecutionContext | None = None
        self._last_context_by_kind: dict[ExecutionKind, ExecutionContext] = {}

    def register(self, execution: LLMExecution, context: ExecutionContext) -> None:
        self._executions[execution.id] = execution
        self._contexts[execution.id] = context

        # Only contexts are preserved.
        self._last_context = context
        self._last_context_by_kind[context.kind] = context

        def _deregister(_):
            self._executions.pop(execution.id, None)
            self._contexts.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)

    def select(self, query: ExecutionQuery | None = None) -> Sequence[LLMExecution]:
        target_ids = list(self._executions.keys())
        query = query or ExecutionQuery()
        if query.kind is not None:
            target_ids = [id_ for id_ in target_ids if self._contexts[id_].kind == query.kind]
        return [self._executions[id_] for id_ in target_ids]

    def get_running(
        self, kind: ExecutionKind | None = None
    ) -> Sequence[LLMExecution]:
        query = ExecutionQuery(kind=kind)
        return self.select(query)

    @property
    def last_context(self) -> ExecutionContext | None:
        return self._last_context

    def get_last_context_by_kind(self, kind: ExecutionKind) -> ExecutionContext | None:
        return self._last_context_by_kind.get(kind)

    def can_execute(self, policy: ExecutionPolicy) -> bool:
        if policy.allow_parallel:
            return True
        if policy.kind is None:
            return not self._executions
        return not (any(self._contexts[id_].kind == policy.kind for id_ in self._executions))