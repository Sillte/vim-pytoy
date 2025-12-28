from pytoy.infra.timertask import TimerTask 
from pytoy.infra.timertask import ThreadWorker 

global MY_NUMBER
MY_NUMBER = 100

def func():
    global MY_NUMBER 
    MY_NUMBER += 1

s = TimerTask.register(func, interval=10)


def main_func() -> str:
    import time
    time.sleep(1)
    return "from_main_func"

def on_finish(mes: str):
    print(f"{MY_NUMBER=} on_finish with {mes=}")
    assert 100 < MY_NUMBER

ThreadWorker.run(main_func=main_func, on_finish=on_finish)