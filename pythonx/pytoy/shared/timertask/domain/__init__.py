from dataclasses import dataclass
from typing import Callable, Literal, Protocol

from pytoy.shared.lib.event import EventProtocol
from pytoy.shared.lib.outcome import Outcome

type TaskName = str
type VimFuncName = str
type FunctionName = str

type NormalStopReason = Literal["finished", "stopped"]  # `repeat` is comsued or exeception is raised.

type OnTaskCallback = Callable[[], None]
type OnFinishCallback = Callable[[NormalStopReason], None] | Callable[[], None]
type OnErrorCallback = Callable[[Exception], None] | Callable[[], None]


@dataclass(frozen=True)
class TaskExit:
    id: TaskName
    outcome: Outcome[NormalStopReason, Exception]


class TimerStopException(Exception):
    """Exception raised inside the timer callback to stop the registered loop.
    When this exception is raised, the `on_finish` callback is invoked with
    the ``"stopped"`` reason and `on_error` is not invoked.
    """

    pass


class TimerTaskImplProtocol(Protocol):
    @property
    def on_exit(self) -> EventProtocol[TaskExit]: ...

    @property
    def on_registered(self) -> EventProtocol[TaskName]: ...

    @property
    def on_deregistered(self) -> EventProtocol[TaskName]: ...

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
    ) -> TaskName: ...

    def deregister(self, name: TaskName, *, strict: bool = False) -> None: ...

    def is_registered(self, name: TaskName) -> bool: ...


@dataclass(frozen=True)
class RegisteredTask:
    name: TaskName
    function: Callable[[], None]
    impl_function_name: FunctionName
    initial_repeat: int = -1


@dataclass
class TaskStatus:
    """Status of a TimerTask, which may change during execution."""

    repeat: int


class BackendThreadUtilProtocol(Protocol):
    def prepare(self) -> None: ...
    def add_message(self, message: str) -> None: ...
