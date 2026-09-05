def test_naive2():

    import threading
    from unittest.mock import MagicMock

    from pytoy.shared.timertask.thread_execution import ThreadExecutionHooks, ThreadExecutionRequest, ThreadExecutor
    from pytoy.shared.timertask.thread_execution.manager import ThreadExecutionManager

    # 簡単な task
    def simple_task(cancel_token):
        for i in range(3):
            if cancel_token.is_set():
                return "cancelled"
        return 42

    executor = ThreadExecutor(manager=ThreadExecutionManager())
    result_notified = threading.Event()
    on_result = MagicMock(side_effect=lambda _: result_notified.set())
    hooks = ThreadExecutionHooks(on_result=on_result, on_exception=MagicMock())

    request = ThreadExecutionRequest.from_any(
        main_func=simple_task,
    )
    executor.execute(request, hooks=hooks)
    assert result_notified.wait(1)
    on_result.assert_called_once_with(42)
    hooks.on_exception.assert_not_called()  # type:ignore
