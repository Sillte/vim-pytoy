import threading

import pytest

from pytoy.shared.timertask import TimerTask
from pytoy.shared.timertask.thread_execution import ThreadExecutionHooks, ThreadExecutionRequest, ThreadExecutor


def test_thread_executor_accepts_timer_task_dispatch_thread() -> None:
    result_received = threading.Event()
    results: list[int] = []

    def on_result(result: int) -> None:
        results.append(result)
        result_received.set()

    def start_execution() -> None:
        ThreadExecutor().execute(
            ThreadExecutionRequest.from_any(lambda _: 42),
            ThreadExecutionHooks.from_any(on_result=on_result),
        )

    TimerTask.execute_oneshot(start_execution, interval=0)

    assert result_received.wait(timeout=5)
    assert results == [42]


def test_failed_repeated_start_keeps_the_existing_execution_registered() -> None:
    worker_started = threading.Event()
    release_worker = threading.Event()
    result_received = threading.Event()
    results: list[int] = []

    def worker(_) -> int:
        worker_started.set()
        release_worker.wait(timeout=5)
        return 42

    def on_result(result: int) -> None:
        results.append(result)
        result_received.set()

    handler = ThreadExecutor().execute(
        ThreadExecutionRequest.from_any(worker),
        ThreadExecutionHooks.from_any(on_result=on_result),
    )

    try:
        assert worker_started.wait(timeout=5)
        with pytest.raises(RuntimeError, match="must be `created`"):
            handler.start()
        assert handler.status == "running"
    finally:
        release_worker.set()

    assert result_received.wait(timeout=5)
    assert results == [42]
    assert results == [42]
