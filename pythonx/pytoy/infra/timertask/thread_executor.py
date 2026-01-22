from pytoy.infra.timertask.stdout_rescuer import StdoutProxy
from pytoy.infra.timertask.timer import TimerTask, TimerStopException
from pytoy.contexts.core import GlobalCoreContext 

import threading
from queue import Queue, Empty
from typing import Callable, Any, Literal

from dataclasses import dataclass
from threading import Thread, Event


type ResultType = Literal["Finished", "Error"]
type ThreadID = int
type CancelToken = Event


@dataclass
class ThreadExecution:
    thread: Thread
    cancel_token: CancelToken
    on_finish: Callable[[Any], None]
    on_error: Callable[[Exception], None]

    @property
    def id(self) -> ThreadID:
        if self.thread.native_id is None:
            raise RuntimeError("Thread is not running yet.")
        return self.thread.native_id

    @property
    def alive(self) -> bool:
        return self.thread.is_alive()

    def cancel(self) -> None:
        """Request cancellation. The main_func must check cancel_token.is_set()."""
        self.cancel_token.set()


@dataclass
class ThreadExecutionRequest:
    """
    It is better for `main_func` to get the `CancelToken` and
    check periodically `is_set`.
    """

    main_func: Callable[[CancelToken], Any]  # It is accepted if CancelToken is not set.
    on_finish: Callable[[Any], None]
    on_error: Callable[[Exception], None]

    def __post_init__(self) -> None:
        self.main_func = self._solve_main_func(self.main_func)

    def _solve_main_func(self, main_func: Callable[[CancelToken], Any] | Callable[[], Any]) -> Callable[[CancelToken], Any]:
        """Wrap the function without the argument.
        """
        from inspect import signature, Parameter
        from functools import wraps

        sig = signature(self.main_func)
        params = list(sig.parameters.values())

        if len(params) == 0 or all(p.default is not Parameter.empty for p in params):
            original = self.main_func

            @wraps(original)
            def wrapper(event: Event) -> Any:
                return original() # type: ignore
            return wrapper
        return main_func # type: ignore


@dataclass(frozen=True)
class ExecutionResult:
    id: ThreadID
    result_type: ResultType
    result: Any | None = None
    exception: Exception | None = None


class ThreadExecutionManager:
    def __init__(self):
        self._executions: dict[ThreadID, ThreadExecution] = {}
        self._queue: Queue[ExecutionResult] = Queue()
        self._started: bool = False
        self._timertask_name: None | str = None

    def assert_main_thread(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("ThreadExecutionManager methods must be called from the main thread.")

    @property
    def queue(self) -> Queue[ExecutionResult]:
        return self._queue

    @property
    def executions(self) -> dict[ThreadID, ThreadExecution]:
        return self._executions


    def _start(self) -> None:
        if not self._started:
            self._timertask_name = TimerTask.register(self._polling, interval=200)
            self._started = True
            StdoutProxy.ensure_activate()


    def start_and_register(self, thread: Thread, cancel_token: Event, request: ThreadExecutionRequest) -> ThreadExecution:
        self.assert_main_thread()
        # NOTE: It is important to prepare the environment where execution of Thread is possible.
        # E.g., refer to `StdoutProxy`. 
        self._start()
        thread.start()
        execution = ThreadExecution(
            thread=thread,
            cancel_token=cancel_token,
            on_finish=request.on_finish,
            on_error=request.on_error,
        )
        self._executions[execution.id] = execution
        return execution


    def cancel(self, id: ThreadID) -> None:
        """It only requests cancel to `main_function`. 
        It is caller's responsibility that `cancel.is_set` is checked, 
        periodically. 
        """
        self.assert_main_thread()
        self._executions[id].cancel_token.set()


    def _polling(self) -> None:
        while True:
            try:
                result: ExecutionResult = self._queue.get_nowait()
            except Empty:
                break

            execution = self._executions.get(result.id)
            if not execution:
                continue

            self._consume_execution_result(execution, result)
            self._executions.pop(result.id)

        if not self._executions:
            self._started = False
            raise TimerStopException()

    def _consume_execution_result(self, execution: ThreadExecution, result: ExecutionResult):
        self.assert_main_thread()
        if result.result_type == "Finished":
            execution.on_finish(result.result)
        elif result.result_type == "Error":
            if result.exception:
                execution.on_error(result.exception)
            else:
                raise ValueError("Implementation Error: missing exception")
        else:
            raise ValueError("Implementation Error: invalid result_type")


class ThreadExecutor:
    def __init__(self, *, ctx: GlobalCoreContext | None = None):
        if ctx is None:
            ctx = GlobalCoreContext.get()
        self._execution_manager = ctx.thread_execution_manager
        self._queue = self._execution_manager.queue

    def execute(self, request: ThreadExecutionRequest) -> ThreadExecution:
        cancel_token = Event()

        def _run(event: Event):
            thread_id = threading.get_native_id()
            try:
                ret = request.main_func(event)
            except Exception as e:
                result = ExecutionResult(id=thread_id, result_type="Error", exception=e)
            else:
                result = ExecutionResult(id=thread_id, result_type="Finished", result=ret)
            self._queue.put(result)

        thread = Thread(target=_run, daemon=True, args=(cancel_token,))
        return self._execution_manager.start_and_register(thread, cancel_token, request)
    
if __name__ == "__main__":
    pass
    import time

    # ダミーの GlobalCoreContext を作る
    class DummyContext:
        class DummyManager:
            def __init__(self):
                self.thread_execution_manager = ThreadExecutionManager()

            def get(self):
                return self

        def get(self):
            return DummyContext.DummyManager()

    ctx = DummyContext().get()

    executor = ThreadExecutor(ctx=ctx)

    # finish / error callback
    def on_finish(result):
        print(f"[FINISH] result={result}")

    def on_error(exc):
        print(f"[ERROR] exception={exc}")

    # 簡単な task
    def simple_task(cancel_token):
        print("Task started")
        for i in range(3):
            if cancel_token.is_set():
                print("Task cancelled")
                return "cancelled"
            print(f"Working {i+1}/3")
            time.sleep(0.5)
        print("Task finished")
        return 42

    request = ThreadExecutionRequest(
        main_func=simple_task,
        on_finish=on_finish,
        on_error=on_error
    )

    exec_obj = executor.execute(request)

    # polling を強制的に回す（通常は TimerTask が回す）
    while exec_obj.alive:
        ctx.thread_execution_manager._polling()
        time.sleep(0.1)

    print("All done.")
