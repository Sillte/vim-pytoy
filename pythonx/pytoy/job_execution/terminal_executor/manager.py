from pytoy.job_execution.terminal_executor.models import ExecutionContext, ExecutionID, DriverKind, ExecutionPolicy, ExecutionQuery, TerminalExecution
from pytoy.shared.ui.pytoy_buffer import BufferSource


from typing import Sequence


class TerminalExecutionManager:
    def __init__(self):
        self._executions: dict[ExecutionID, TerminalExecution] = {}
        self._contexts: dict[ExecutionID, ExecutionContext] = {}

        # Last_context remains even if the execution ends. 
        self._last_context_by_kind: dict[DriverKind, ExecutionContext] = {}
        self._last_context = None

    def register(self, execution: TerminalExecution, context: ExecutionContext):
        self._executions[execution.id] = execution
        self._contexts[execution.id] = context
        self._last_context = context
        self._last_context_by_kind[context.kind] = context
        def _deregister(_):
            self._executions.pop(execution.id, None)
            self._contexts.pop(execution.id, None)
        execution.events.on_job_exit.subscribe(_deregister)


    def select(self, query: ExecutionQuery | None = None) -> Sequence[TerminalExecution]:
        query = query or ExecutionQuery()
        target_ids = list(self._executions.keys())
        if query.buffer is not None:
            target_ids = [elem for elem in target_ids if self._executions[elem].runner.buffer.source == query.buffer]
        if query.kind is not None:
            target_ids = [elem for elem in target_ids if self._contexts[elem].kind == query.kind]
        return [self._executions[elem] for elem in target_ids]


    @property
    def last_context(self) -> ExecutionContext | None:
        return self._last_context

    def get_last_context_by_name(self, kind: DriverKind) -> ExecutionContext | None:
        return self._last_context_by_kind.get(kind)

    def get_running(self, kind: DriverKind | None = None, buffer: BufferSource | None = None) -> Sequence[TerminalExecution]:
        query = ExecutionQuery(kind=kind, buffer=buffer)
        return self.select(query)

    def can_execute(self, policy: ExecutionPolicy) -> bool:
        source = policy.buffer_request.source
        if self.select(ExecutionQuery(buffer=source)):
            return False
        return True