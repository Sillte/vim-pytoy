import threading

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
