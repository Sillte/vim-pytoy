import threading
from typing import Sequence

from pytoy.shared.ui.pytoy_buffer import BufferSource

from .models import (
    TerminalDriverKind,
    TerminalExecution,
    TerminalExecutionContext,
    TerminalExecutionID,
    TerminalExecutionQuery,
)


class TerminalExecutionManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._executions: dict[TerminalExecutionID, TerminalExecution] = {}

        # Last_context remains even if the execution ends.
        self._last_context_by_kind: dict[TerminalDriverKind, TerminalExecutionContext] = {}
        self._last_context = None

    def register(self, execution: TerminalExecution):
        with self._lock:
            self._executions[execution.id] = execution

        def _deregister(_):
            with self._lock:
                self._executions.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)

    def register_context(self, context: TerminalExecutionContext):
        with self._lock:
            self._last_context = context
            self._last_context_by_kind[context.kind] = context

    def select(self, query: TerminalExecutionQuery | None = None) -> Sequence[TerminalExecution]:
        query = query or TerminalExecutionQuery()
        with self._lock:
            executions = list(self._executions.values())

        if query.buffer is not None:
            executions = [execution for execution in executions if execution.runner.buffer.source == query.buffer]
        if query.kind is not None:
            executions = [execution for execution in executions if execution.kind == query.kind]
        if query.status is not None:
            executions = [execution for execution in executions if execution.status == query.status]
        return executions

    @property
    def last_context(self) -> TerminalExecutionContext | None:
        with self._lock:
            return self._last_context

    def get(self, execution_id: TerminalExecutionID) -> TerminalExecution | None:
        with self._lock:
            return self._executions.get(execution_id)

    def get_last_context_by_name(self, kind: TerminalDriverKind) -> TerminalExecutionContext | None:
        with self._lock:
            return self._last_context_by_kind.get(kind)

    def get_running(
        self, kind: TerminalDriverKind | None = None, buffer: BufferSource | None = None
    ) -> Sequence[TerminalExecution]:
        query = TerminalExecutionQuery(kind=kind, buffer=buffer, status="running")
        return self.select(query)
