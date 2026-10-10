from queue import Empty, Queue
from threading import RLock
from typing import Callable, Sequence

from pytoy.shared.lib.backend import can_use_vim
from pytoy.shared.timertask import TimerTask, backend_thread_dispatch
from pytoy.shared.timertask.domain import BackendThreadUtilProtocol

from .models import ThreadExecution, ThreadExecutionExit, ThreadExecutionID, ThreadExecutionQuery, ThreadExecutionStatus


class ThreadExecutionManager:
    def __init__(self):
        self._lock = RLock()
        self._executions: dict[ThreadExecutionID, ThreadExecution] = {}
        self._queue: Queue[ThreadExecutionExit] = Queue()
        self._consumer = _ThreadExecutionConsumer(queue=self._queue, consume=self._consume)

    def register(self, execution: ThreadExecution) -> ThreadExecution:
        with self._lock:
            self._executions[execution.id] = execution

        def _deregister(_):
            with self._lock:
                self._executions.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)
        return execution

    def get_execution(self, execution_id: ThreadExecutionID) -> ThreadExecution | None:
        with self._lock:
            return self._executions.get(execution_id)

    def get_status(self, execution_id: ThreadExecutionID) -> ThreadExecutionStatus | None:
        with self._lock:
            execution = self._executions.get(execution_id)
            return execution.status if execution is not None else None

    def start_execution[T](self, execution_id: ThreadExecutionID, start: Callable[[ThreadExecution[T]], None]) -> None:
        """Start an execution atomically, leaving it registered if startup fails."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                raise ValueError(f"`execution` does not exist; {execution_id=}")
            start(execution)

    def discard_unstarted(self, execution_id: ThreadExecutionID) -> None:
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                return
            if not self._discard_unstarted_locked(execution_id, execution):
                raise RuntimeError("Only an unstarted execution can be discarded.")

    def _discard_unstarted_locked(self, execution_id: ThreadExecutionID, execution: ThreadExecution) -> bool:
        if execution.status != "created" or self._executions.get(execution_id) is not execution:
            return False
        del self._executions[execution_id]
        execution.exit_emitter.dispose()
        return True

    def submit_exit_entity(self, result: ThreadExecutionExit) -> None:
        self._queue.put(result)

    def select(self, query: ThreadExecutionQuery | None = None) -> Sequence[ThreadExecution]:
        query = query or ThreadExecutionQuery()
        with self._lock:
            executions = tuple(self._executions.values())
            if query.id is not None:
                executions = tuple(item for item in executions if item.id == query.id)
            if query.statuses is not None:
                statuses = set(query.statuses)
                executions = tuple(item for item in executions if item.status in statuses)
            if query.kind is not None:
                executions = tuple(item for item in executions if item.kind == query.kind)
            return executions

    def _consume(self, execution_exit: ThreadExecutionExit) -> None:
        execution = self.get_execution(execution_exit.id)
        if not execution:
            return
        backend_thread_dispatch(lambda: execution.notify_exit(execution_exit))


def add_log_message(message: str) -> None:
    """Add log message to the stdout. It is used for debugging."""
    # [TODO]: Once the enum which represents the environment background (vim / nvim / vscode / fake...), then
    # change the function.
    get_backend_thread_util().add_message(message)


def get_backend_thread_util() -> BackendThreadUtilProtocol:
    """Get the backend thread util implementation."""
    if can_use_vim():
        from pytoy.shared.timertask.impls.vim.stdout_rescuer import VimThreadUtil

        return VimThreadUtil()
    else:
        from pytoy.shared.timertask.impls.dummy import DummyThreadUtil

        return DummyThreadUtil()


class _ThreadExecutionConsumer:
    def __init__(
        self,
        queue: Queue[ThreadExecutionExit],
        consume: Callable[[ThreadExecutionExit], None],
        interval: int = 200,
        backend_thread_util: BackendThreadUtilProtocol | None = None,
    ):
        self._queue = queue
        self._consume = consume
        self._interval = interval
        self._backend_thread_util = backend_thread_util or get_backend_thread_util()
        self._started: bool = False
        self._timertask_name: None | str = None
        self._start()

    def _start(self) -> None:
        if not self._started:
            self._timertask_name = TimerTask.register(self._polling, interval=self._interval)
            self._started = True
            self._backend_thread_util.prepare()

    def _polling(self) -> None:
        while True:
            try:
                exit_entity: ThreadExecutionExit = self._queue.get_nowait()
            except Empty:
                break
            self._consume(exit_entity)
