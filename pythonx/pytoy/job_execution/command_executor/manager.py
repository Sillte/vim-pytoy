from pytoy.job_execution.command_executor.models import (
    CommandExecution,
    CommandExecutionContext,
    CommandExecutionID,
    CommandExecutionKind,
    ExecutionPolicy,
    ExecutionQuery,
)
from pytoy.shared.ui.pytoy_buffer import BufferSource


from typing import Sequence


class CommandExecutionManager:
    def __init__(self):
        self._executions: dict[CommandExecutionID, CommandExecution] = {}
        self._contexts: dict[CommandExecutionID, CommandExecutionContext] = {}
        self._last_context_by_kind: dict[CommandExecutionKind, CommandExecutionContext] = {}
        self._last_context = None

    def register(self, execution: CommandExecution, context: CommandExecutionContext):
        self._executions[execution.id] = execution
        self._contexts[execution.id] = context

        # Only contexts are preserved.
        self._last_context = context
        self._last_context_by_kind[context.kind] = context

        def _deregister(_):
            self._executions.pop(execution.id, None)
            self._contexts.pop(execution.id, None)

        execution.events.on_job_exit.subscribe(_deregister)

    def select(self, query: ExecutionQuery | None = None) -> Sequence[CommandExecution]:
        target_ids = list(self._executions.keys())
        query = query or ExecutionQuery()
        if query.kind is not None:
            target_ids = [id_ for id_ in target_ids if self._contexts[id_].kind == query.kind]
        if query.stdout is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].runner.stdout.source == query.stdout]
        return [self._executions[id_] for id_ in target_ids]

    def get_running(
        self, kind: CommandExecutionKind | None = None, stdout: BufferSource | None = None
    ) -> Sequence[CommandExecution]:
        query = ExecutionQuery(kind=kind, stdout=stdout)
        return self.select(query)

    @property
    def last_context(self) -> CommandExecutionContext | None:
        return self._last_context

    def get_last_context_by_kind(self, kind: CommandExecutionKind) -> CommandExecutionContext | None:
        return self._last_context_by_kind.get(kind)
