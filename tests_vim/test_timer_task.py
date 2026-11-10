from pytoy.shared.timer_task import TimerTaskScheduler

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


TimerTaskScheduler().register(
    func,
    interval=10,
    on_finish=on_finish_timer,
    on_error=on_error_timer,
    repeat=20,
)
