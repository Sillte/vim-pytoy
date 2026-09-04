import threading
from queue import Empty, Queue
from typing import Callable, Sequence

from pytoy.shared.lib.backend import can_use_vim
from pytoy.shared.timertask.domain import BackendThreadUtilProtocol
from pytoy.shared.timertask.timer import TimerTask

from .models import ThreadExecution, ThreadExecutionExit, ThreadExecutionID, ThreadExecutionQuery


class ThreadExecutionManager:
    def __init__(self):
        self._executions: dict[ThreadExecutionID, ThreadExecution] = {}
        self._queue: Queue[ThreadExecutionExit] = Queue()
        self._consumer = _ThreadExecutionConsumer(queue=self._queue, consume=self._consume)

    def register(self, execution: ThreadExecution) -> ThreadExecution:
        self._executions[execution.id] = execution

        def _deregister(_):
            self._executions.pop(execution.id, None)

        execution.on_exit.subscribe(_deregister)
        return execution

    def get_execution(self, execution_id: ThreadExecutionID) -> ThreadExecution | None:
        return self._executions.get(execution_id)

    def submit_exit_entity(self, result: ThreadExecutionExit) -> None:
        self._queue.put(result)

    def select(self, query: ThreadExecutionQuery | None = None) -> Sequence[ThreadExecution]:
        target_ids = list(self._executions.keys())
        query = query or ThreadExecutionQuery()
        if query.id is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].id == query.id]
        if query.statuses is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].status in set(query.statuses)]
        if query.kind is not None:
            target_ids = [id_ for id_ in target_ids if self._executions[id_].kind == query.kind]
        return [self._executions[id_] for id_ in target_ids]

    def _consume(self, execution_exit: ThreadExecutionExit) -> None:
        self.assert_main_thread()

        execution = self._executions.get(execution_exit.id)
        if not execution:
            return
        execution.notify_exit(execution_exit)

    def assert_main_thread(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("ThreadExecutionConsumer methods must be called from the main thread.")


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
