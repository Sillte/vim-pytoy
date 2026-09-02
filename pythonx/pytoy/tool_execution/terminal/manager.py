from typing import Sequence

from pytoy.shared.ui.pytoy_buffer import BufferSource

from .models import (
    TerminalDriverKind,
    TerminalExecution,
    TerminalExecutionContext,
    TerminalExecutionID,
    TerminalExecutionPolicy,
    TerminalExecutionQuery,
)


class TerminalExecutionManager:
    def __init__(self):
        self._executions: dict[TerminalExecutionID, TerminalExecution] = {}

        # Last_context remains even if the execution ends.
        self._last_context_by_kind: dict[TerminalDriverKind, TerminalExecutionContext] = {}
        self._last_context = None

    def register(self, execution: TerminalExecution):
        self._executions[execution.id] = execution

        def _deregister(_):
            self._executions.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)

    def register_context(self, context: TerminalExecutionContext):
        self._last_context = context
        self._last_context_by_kind[context.kind] = context

    def select(self, query: TerminalExecutionQuery | None = None) -> Sequence[TerminalExecution]:
        query = query or TerminalExecutionQuery()
        target_ids = list(self._executions.keys())
        if query.buffer is not None:
            target_ids = [elem for elem in target_ids if self._executions[elem].runner.buffer.source == query.buffer]
        if query.kind is not None:
            target_ids = [elem for elem in target_ids if self._executions[elem].kind == query.kind]
        if query.status is not None:
            target_ids = [elem for elem in target_ids if self._executions[elem].status == query.status]
        return [self._executions[elem] for elem in target_ids]

    @property
    def last_context(self) -> TerminalExecutionContext | None:
        return self._last_context

    def get(self, execution_id: TerminalExecutionID) -> TerminalExecution | None:
        return self._executions.get(execution_id)

    def get_last_context_by_name(self, kind: TerminalDriverKind) -> TerminalExecutionContext | None:
        return self._last_context_by_kind.get(kind)

    def get_running(
        self, kind: TerminalDriverKind | None = None, buffer: BufferSource | None = None
    ) -> Sequence[TerminalExecution]:
        query = TerminalExecutionQuery(kind=kind, buffer=buffer)
        return self.select(query)

    def can_execute(self, policy: TerminalExecutionPolicy) -> bool:
        source = policy.buffer_request.source
        if self.select(TerminalExecutionQuery(buffer=source)):
            return False
        return True
