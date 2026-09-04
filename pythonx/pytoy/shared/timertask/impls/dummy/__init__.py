import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from pytoy.shared.timertask.domain import (
    BackendThreadUtilProtocol,
    NormalStopReason,
    OnTaskCallback,
    TaskName,
    TimerStopException,
    TimerTaskImplProtocol,
)


class DummyThreadUtil(BackendThreadUtilProtocol):
    def prepare(self) -> None:
        pass

    def add_message(self, message: str) -> None:
        print(message, flush=True)


@dataclass
class _Task:
    func: OnTaskCallback
    interval: float
    repeat: int
    on_finish: Callable[[NormalStopReason], None] | None = None
    on_error: Callable[[Exception], None] | None = None
    next_run: float = field(default_factory=time.monotonic)
    count: int = 0
    stopped: bool = False


class TimerTaskImplDummy(TimerTaskImplProtocol):
    """Currently, the registered `func` is not executed..."""

    def __init__(self) -> None:
        self.tasks: dict[TaskName, _Task] = {}
        self._scheduled: list[tuple[float, int, TaskName]] = []
        self._sequence = 0
        self._condition = threading.Condition()
        self._scheduler = threading.Thread(target=self._run, name="TimerTaskDummyScheduler", daemon=True)
        self._scheduler.start()

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: Callable[[NormalStopReason], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> TaskName:
        with self._condition:
            self._sequence += 1
            taskname = name or f"AUTONAME{self._sequence}_{id(func)}"
            task = _Task(func, interval / 1000, repeat, on_finish, on_error)
            self.tasks[taskname] = task
            heapq.heappush(self._scheduled, (task.next_run, self._sequence, taskname))
            self._condition.notify()
        return taskname

    def deregister(self, name: TaskName, *, strict: bool = False) -> None:
        with self._condition:
            task = self.tasks.pop(name, None)
            if not task:
                if strict:
                    raise KeyError(f"Task {name} is not registered.")
                return
            task.stopped = True
            self._condition.notify()

    def is_registered(self, name: TaskName) -> bool:
        with self._condition:
            return name in self.tasks

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._scheduled:
                    self._condition.wait()

                next_run, _, task_name = self._scheduled[0]
                delay = next_run - time.monotonic()
                if delay > 0:
                    self._condition.wait(timeout=delay)
                    continue

                heapq.heappop(self._scheduled)
                task = self.tasks.get(task_name)

            if task is None or task.stopped:
                continue

            try:
                task.func()
            except TimerStopException:
                with self._condition:
                    self.tasks.pop(task_name, None)
                self._invoke_finish(task, "stopped")
                continue
            except Exception as exception:
                with self._condition:
                    self.tasks.pop(task_name, None)
                if task.on_error:
                    try:
                        task.on_error(exception)
                    except Exception:
                        pass
                continue

            with self._condition:
                task.count += 1
                if task.stopped or self.tasks.get(task_name) is not task:
                    stopped = True
                    finished = False
                else:
                    stopped = False
                    finished = task.repeat >= 0 and task.count >= task.repeat
                    if finished:
                        self.tasks.pop(task_name, None)
                    else:
                        task.next_run = time.monotonic() + task.interval
                        self._sequence += 1
                        heapq.heappush(self._scheduled, (task.next_run, self._sequence, task_name))

            if stopped and task.on_finish:
                self._invoke_finish(task, "stopped")
            elif finished and task.on_finish:
                self._invoke_finish(task, "finished")

    @staticmethod
    def _invoke_finish(task: _Task, reason: NormalStopReason) -> None:
        on_finish = task.on_finish
        if on_finish is None:
            return
        try:
            on_finish(reason)
        except Exception as exception:
            if task.on_error:
                try:
                    task.on_error(exception)
                except Exception:
                    pass
