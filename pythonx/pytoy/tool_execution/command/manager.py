import threading
from typing import Sequence

from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_execution.command.models import (
    CommandExecution,
    CommandExecutionContext,
    CommandExecutionID,
    CommandExecutionKind,
    CommandExecutionQuery,
)


class CommandExecutionManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._executions: dict[CommandExecutionID, CommandExecution] = {}
        self._last_context_by_kind: dict[CommandExecutionKind, CommandExecutionContext] = {}
        self._last_context = None

    def register(self, execution: CommandExecution) -> None:
        with self._lock:
            self._executions[execution.id] = execution

        def _deregister(_):
            with self._lock:
                self._executions.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)

    def register_context(self, context: CommandExecutionContext) -> None:
        with self._lock:
            self._last_context = context
            self._last_context_by_kind[context.kind] = context

    def select(self, query: CommandExecutionQuery | None = None) -> Sequence[CommandExecution]:
        query = query or CommandExecutionQuery()
        with self._lock:
            executions = list(self._executions.values())
            if query.kind is not None:
                executions = [execution for execution in executions if execution.kind == query.kind]
            if query.stdout is not None:
                executions = [execution for execution in executions if execution.runner.stdout.source == query.stdout]
            if query.status is not None:
                executions = [execution for execution in executions if execution.status == query.status]
            return executions

    def get(self, id_: CommandExecutionID) -> CommandExecution | None:
        with self._lock:
            return self._executions.get(id_)

    def get_running(
        self, kind: CommandExecutionKind | None = None, stdout: BufferSource | None = None
    ) -> Sequence[CommandExecution]:
        query = CommandExecutionQuery(kind=kind, stdout=stdout, status="running")
        return self.select(query)

    @property
    def last_context(self) -> CommandExecutionContext | None:
        with self._lock:
            return self._last_context

    def get_last_context_by_kind(self, kind: CommandExecutionKind) -> CommandExecutionContext | None:
        with self._lock:
            return self._last_context_by_kind.get(kind)
