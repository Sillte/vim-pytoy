from unittest.mock import MagicMock
from pytoy.infra.timertask.thread_executor import ThreadExecutionManager, ThreadExecutionManager, ThreadExecutor, ThreadExecutionRequest, TimerStopException
import time

def test_naive():
    class DummyContext:
        class DummyContent:
            def __init__(self):
                self.thread_execution_manager = ThreadExecutionManager()
            def get(self):
                return self
        def get(self):
            return DummyContext.DummyContent()

    # 簡単な task
    def simple_task(cancel_token):
        print("Task started")
        for i in range(3):
            if cancel_token.is_set():
                print("Task cancelled")
                return "cancelled"
            print(f"Working {i+1}/3")
            time.sleep(0.1)
        print("Task finished")
        return 42

    ctx = DummyContext().get()
    executor = ThreadExecutor(ctx=ctx) # type: ignore
    on_finish = MagicMock()
    on_error = MagicMock()

    request = ThreadExecutionRequest(
        main_func=simple_task,
        on_finish=on_finish,
        on_error=on_error
    )

    exec_obj = executor.execute(request)

    time.sleep(0.1)

    # polling を強制的に回す（通常は TimerTask が回す）
    while exec_obj.alive:
        time.sleep(0.1)
    try:
        ctx.thread_execution_manager._polling()
    except TimerStopException:
        pass
    on_finish.assert_called_once_with(42)
    on_error.assert_not_called()
    print("All done.")
