from dataclasses import dataclass
from typing import Callable, Self

from pytoy.shared.lib.outcome import Outcome
from pytoy.shared.timertask.thread_execution import CancelToken

type RoutineUnitName = str


@dataclass(frozen=True)
class RoutineContext:
    cancel_token: CancelToken
    unit_name: RoutineUnitName


@dataclass(frozen=True)
class RoutineUnit[T]:
    name: RoutineUnitName
    worker: Callable[[RoutineContext], T]
    delay: int
    max_iteration: int | None


@dataclass(frozen=True)
class RoutineUnitIterationExit[T]:
    name: RoutineUnitName
    outcome: Outcome[T, Exception]


@dataclass(frozen=True)
class RoutineUnitHooks[T]:
    on_result: Callable[[T], None]
    on_exception: Callable[[Exception], None]
    on_exit: Callable[[RoutineUnitIterationExit], None]

    @classmethod
    def from_any(
        cls,
        on_result: Callable[[T], None] | None = None,
        on_exception: Callable[[Exception], None] | None = None,
        on_exit: Callable[[RoutineUnitIterationExit], None] | None = None,
    ) -> Self:
        on_result = on_result or (lambda _: None)
        on_exception = on_exception or (lambda _: None)
        on_exit = on_exit or (lambda _: None)
        return cls(on_result=on_result, on_exception=on_exception, on_exit=on_exit)


@dataclass(frozen=True)
class RoutineUnitRequest[T]:
    name: RoutineUnitName
    worker: Callable[[RoutineContext], T]
    delay: int = 1000
    max_iteration: int | None = None

    @classmethod
    def from_any(
        cls,
        worker: Callable[[RoutineContext], T],
        name: RoutineUnitName = "single-unit",
        delay: int = 1000,
        max_iteration: int | None = None,
    ):
        return cls(name=name, worker=worker, delay=delay, max_iteration=max_iteration)
