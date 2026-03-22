from pytoy.shared.timertask import TimerTask
from pytoy.shared.timertask.thread_executor import ThreadExecutor, ThreadExecutionRequest
from pytoy.contexts.core import GlobalCoreContext

global MY_NUMBER
MY_NUMBER = 100

# --- TimerTask側テスト ---
def func():
    global MY_NUMBER
    MY_NUMBER += 1

def on_finish_timer(reason: str):
    print("Timer finished:", reason)

def on_error_timer(e: Exception):
    print("Timer error:", e, MY_NUMBER)

TimerTask.register(
    func,
    interval=10,
    on_finish=on_finish_timer,
    on_error=on_error_timer,
    repeat=20,
)

# --- ThreadExecutor側テスト ---
def main_func(cancel_token):
    import time
    time.sleep(1)
    return "from_main_func"

def on_finish_thread(result):
    print(f"{MY_NUMBER=} on_finish with result={result}")
    assert 100 < MY_NUMBER

def on_error_thread(e: Exception):
    print("Thread error:", e)

# Context取得
ctx = GlobalCoreContext.get()
executor = ThreadExecutor(ctx=ctx)

request = ThreadExecutionRequest(
    main_func=main_func,
    on_finish=on_finish_thread,
    on_error=on_error_thread,
)

executor.execute(request)