import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.outcome import Error, Success
from pytoy.shared.timertask.domain import (
    BackendThreadUtilProtocol,
    NormalStopReason,
    OnTaskCallback,
    TaskExit,
    TaskName,
    TimerStopException,
    TimerTaskImplProtocol,
)


class DummyThreadUtil:
    def prepare(self) -> None:
        pass

    def add_message(self, message: str) -> None:
        print(message, flush=True)


@dataclass
class _Task:
    func: OnTaskCallback
    interval: float
    repeat: int
    next_run: float = field(default_factory=time.monotonic)
    count: int = 0
    stopped: bool = False


class TimerTaskImplDummy(TimerTaskImplProtocol):
    def __init__(self) -> None:
        self._registered_emitter = EventEmitter[TaskName]()
        self._deregistered_emitter = EventEmitter[TaskName]()
        self._exit_emitter = EventEmitter[TaskExit]()
        self.tasks: dict[TaskName, _Task] = {}
        self._scheduled: list[tuple[float, int, TaskName]] = []
        self._sequence = 0
        self._condition = threading.Condition()
        self._scheduler = threading.Thread(target=self._run, name="TimerTaskDummyScheduler", daemon=True)
        self._scheduler.start()

    @property
    def on_exit(self) -> Event[TaskExit]:
        return self._exit_emitter.event

    @property
    def on_registered(self) -> Event[TaskName]:
        return self._registered_emitter.event

    @property
    def on_deregistered(self) -> Event[TaskName]:
        return self._deregistered_emitter.event

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
    ) -> TaskName:
        with self._condition:
            self._sequence += 1
            taskname = name or f"AUTONAME{self._sequence}_{id(func)}"
            if taskname in self.tasks:
                raise ValueError(f"Task {taskname!r} is already registered.")
            task = _Task(func, interval / 1000, repeat)
            self.tasks[taskname] = task
            heapq.heappush(self._scheduled, (task.next_run, self._sequence, taskname))
            self._condition.notify()
        self._registered_emitter.fire(taskname)
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
        self._deregistered_emitter.fire(name)

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
                self._exit_emitter.fire(TaskExit(task_name, Success("stopped")))
                self._deregistered_emitter.fire(task_name)
                continue
            except Exception as exception:
                with self._condition:
                    self.tasks.pop(task_name, None)
                self._exit_emitter.fire(TaskExit(task_name, Error(exception)))
                self._deregistered_emitter.fire(task_name)
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

            if stopped:
                self._exit_emitter.fire(TaskExit(task_name, Success("stopped")))
            elif finished:
                self._exit_emitter.fire(TaskExit(task_name, Success("finished")))
                self._deregistered_emitter.fire(task_name)
