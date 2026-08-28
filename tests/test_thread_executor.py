def test_naive2():

    import time
    from unittest.mock import MagicMock

    from pytoy.shared.lib.outcome import Success
    from pytoy.shared.timertask.thread_execution import ThreadExecutionHooks, ThreadExecutionRequest, ThreadExecutor
    from pytoy.shared.timertask.thread_execution.manager import ThreadExecutionManager
    from pytoy.shared.timertask.thread_execution.models import ThreadExecutionExit

    # 簡単な task
    def simple_task(cancel_token):
        print("Task started")
        for i in range(3):
            if cancel_token.is_set():
                print("Task cancelled")
                return "cancelled"
            print(f"Working {i + 1}/3")
            time.sleep(0.1)
        print("Task finished")
        return 42

    executor = ThreadExecutor(manager=ThreadExecutionManager())
    hooks = ThreadExecutionHooks(on_finish=MagicMock(), on_exception=MagicMock())

    request = ThreadExecutionRequest.from_any(
        main_func=simple_task,
    )
    handler = executor.execute(request, hooks=hooks)
    id_ = handler.id

    time.sleep(0.1)
    handler._manager._consumer._queue.put(ThreadExecutionExit(id=id_, outcome=Success(value=42)))
    handler._manager._consumer._polling()

    hooks.on_finish.assert_called_once_with(42)  # type:ignore
    hooks.on_exception.assert_not_called()  # type:ignore
