from typing import Sequence

from pytoy.job_execution.command_executor.models import (
    CommandExecution,
    CommandExecutionContext,
    CommandExecutionID,
    CommandExecutionKind,
    CommandExecutionQuery,
)
from pytoy.shared.ui.pytoy_buffer import BufferSource


class CommandExecutionManager:
    def __init__(self):
        self._executions: dict[CommandExecutionID, CommandExecution] = {}
        self._last_context_by_kind: dict[CommandExecutionKind, CommandExecutionContext] = {}
        self._last_context = None

    def register(self, execution: CommandExecution) -> None:
        self._executions[execution.id] = execution

        def _deregister(_):
            self._executions.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)

    def register_context(self, context: CommandExecutionContext) -> None:
        self._last_context = context
        self._last_context_by_kind[context.kind] = context

    def select(self, query: CommandExecutionQuery | None = None) -> Sequence[CommandExecution]:
        target_ids = list(self._executions.keys())
        query = query or CommandExecutionQuery()
        if query.kind is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].kind == query.kind]
        if query.stdout is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].runner.stdout.source == query.stdout]
        return [self._executions[id_] for id_ in target_ids]

    def get(self, id_: CommandExecutionID) -> CommandExecution | None:
        return self._executions.get(id_)

    def get_running(
        self, kind: CommandExecutionKind | None = None, stdout: BufferSource | None = None
    ) -> Sequence[CommandExecution]:
        query = CommandExecutionQuery(kind=kind, stdout=stdout)
        return self.select(query)

    @property
    def last_context(self) -> CommandExecutionContext | None:
        return self._last_context

    def get_last_context_by_kind(self, kind: CommandExecutionKind) -> CommandExecutionContext | None:
        return self._last_context_by_kind.get(kind)
