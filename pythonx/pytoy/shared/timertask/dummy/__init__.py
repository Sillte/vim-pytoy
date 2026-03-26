from pytoy.shared.timertask.domain import (
    TimerTaskImplProtocol,
    TaskName,
    OnTaskCallback,
    NormalStopReason,
)
from typing import Callable
import time
import threading


class _Task:
    def __init__(
        self,
        func: Callable,
        interval: int,
        repeat: int,
        on_finish: Callable[[NormalStopReason], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ):
        self.func = func
        self.interval = interval / 1000  # ms → sec
        self.repeat = repeat
        self.on_finish = on_finish
        self.on_error = on_error
        self.stop: bool = False
        self._lock = threading.Lock()

    def run(self):
        count = 0
        try:
            while True:
                if self.stop:
                    if self.on_finish:
                        self.on_finish("stopped")
                    return
                self.func()
                count += 1

                if self.repeat >= 0 and count >= self.repeat:
                    break

                time.sleep(self.interval)

            if self.on_finish:
                self.on_finish("finished")

        except Exception as e:
            if self.on_error:
                self.on_error(e)


class TimerTaskImplDummy(TimerTaskImplProtocol):
    """Currently, the registered `func` is not executed..."""

    def __init__(self):
        self.tasks: dict[TaskName, _Task] = dict()
        self._lock = threading.Lock()

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: Callable[[NormalStopReason], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> TaskName:
        taskname = name or f"AUTONAME{len(self.tasks) + 1}_{id(func)}"
        with self._lock:
            task = _Task(func, interval, repeat, on_finish, on_error)
            self.tasks[taskname] = task
        threading.Thread(target=task.run, daemon=True).start()
        return taskname

    def deregister(self, name: TaskName, *, strict: bool = False) -> None:
        with self._lock:
            task = self.tasks.get(name)
            if not task:
                if strict:
                    raise KeyError(f"Task {name} is not registered.")
                return
            task.stop = True
            del self.tasks[name]

    def is_registered(self, name: TaskName) -> bool:
        return name in self.tasks
