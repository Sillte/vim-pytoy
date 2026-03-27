from typing import Callable, Any, Literal, Protocol, Self
from textwrap import dedent
from dataclasses import dataclass


type TaskName = str
type VimFuncName = str
type FunctionName = str

type NormalStopReason = Literal["finished", "stopped"]  # `repeat` is comsued or exeception is raised.

type OnTaskCallback = Callable[[], None]
type OnFinishCallback = Callable[[NormalStopReason], None] | Callable[[], None]
type OnErrorCallback = Callable[[Exception], None] | Callable[[], None]


class TimerStopException(Exception):
    """Exception raised inside the timer callback to stop the registered loop.
    Note that when this exception is raised, `on_finish` callback is invoked with 'stopped' reason.
    """

    pass


class TimerTaskImplProtocol(Protocol):
    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: Callable[[NormalStopReason], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> TaskName: ...

    def deregister(self, name: TaskName, *, strict: bool = False) -> None: ...

    def is_registered(self, name: TaskName) -> bool: ...


class TimerTaskImplDummy(TimerTaskImplProtocol):
    """Currently, the registered `func` is not executed..."""

    def __init__(self):
        self.tasks: dict[TaskName, OnTaskCallback] = dict()

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: Callable[[NormalStopReason], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> TaskName:
        taskname = name or f"AUTONAME{len(self.tasks) + 1}"
        self.tasks[taskname] = func
        return taskname

    def deregister(self, name: TaskName, *, strict: bool = False) -> None:
        if name not in self.tasks:
            if strict:
                raise KeyError(f"Task {name} is not registered.")
            else:
                return
        del self.tasks[name]

    def is_registered(self, name: TaskName) -> bool:
        return name in self.tasks


@dataclass(frozen=True)
class RegisteredTask:
    name: TaskName
    function: Callable[[], None]
    impl_function_name: FunctionName
    on_finish: Callable[[NormalStopReason], None] | None = None
    on_error: Callable[[Exception], None] | None = None
    initial_repeat: int = -1


@dataclass
class TaskStatus:
    """Status of a TimerTask, which may change during execution."""

    repeat: int


class BackendThreadUtilProtocol(Protocol):
    def prepare(self) -> None: ...
    def add_message(self, message: str) -> None: ...


class FakeThreadUtil(BackendThreadUtilProtocol):
    """Fake implementation of BackendThreadUtilProtocol for testing purposes."""

    def prepare(self) -> None:
        pass

    def add_message(self, message: str) -> None:
        print(message, flush=True)
