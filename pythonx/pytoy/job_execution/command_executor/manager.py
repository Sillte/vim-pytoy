from pytoy.job_execution.command_executor.models import CommandExecution, ExecutionContext, ExecutionID, ExecutionKind, ExecutionPolicy, ExecutionQuery
from pytoy.shared.ui.pytoy_buffer import BufferSource


from typing import Sequence


class CommandExecutionManager:
    def __init__(self):
        self._executions: dict[ExecutionID, CommandExecution] = {}
        self._contexts: dict[ExecutionID, ExecutionContext] = {}
        self._last_context_by_kind: dict[ExecutionKind, ExecutionContext] = {}
        self._last_context = None


    def register(self, execution: CommandExecution, context: ExecutionContext):
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

    def get_running(self, kind: ExecutionKind | None = None, stdout: BufferSource | None = None) -> Sequence[CommandExecution]:
        query = ExecutionQuery(kind=kind, stdout=stdout)
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
            return (not self._executions)
        return not (any(self._contexts[id_].kind == policy.kind for id_ in self._executions))