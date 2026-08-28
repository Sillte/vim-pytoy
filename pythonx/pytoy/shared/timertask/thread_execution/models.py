from __future__ import annotations
from typing import Callable, cast, Literal, Self, Sequence, assert_never
from threading import Thread
from threading import Event as ThreadingEvent
from dataclasses import dataclass, field
import uuid

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.outcome import Outcome, Success, Error

type ThreadExecutionID = str
type CancelToken = ThreadingEvent
type ThreadExecutionStatus = Literal["created", "running", "finished", "error"]


@dataclass(frozen=True)
class ThreadExecutionExit[T]:
    id: ThreadExecutionID
    outcome: Outcome[T, Exception]


@dataclass(frozen=True)
class ThreadExecutionHooks[T]:
    on_finish: Callable[[T], None]
    on_exception: Callable[[Exception], None]

    @classmethod
    def from_any(
        cls, on_finish: Callable[[T], None] | None = None, on_exception: Callable[[Exception], None] | None = None
    ) -> Self:
        return cls(on_finish=(on_finish or (lambda _: None)), on_exception=(on_exception or (lambda _: None)))


@dataclass
class ThreadExecution[T]:
    thread: Thread
    cancel_token: CancelToken
    id: ThreadExecutionID = field(default_factory=lambda: str(uuid.uuid4()))
    status: ThreadExecutionStatus = "created"
    exit_emitter: EventEmitter[ThreadExecutionExit[T]] = field(default_factory=EventEmitter)
    kind: str = "$default"

    @property
    def on_exit(self) -> Event[ThreadExecutionExit[T]]:
        return self.exit_emitter.event

    def start(self) -> None:
        if self.status != "created":
            raise RuntimeError(f"When `start` is called, `status` must be `created`, but `{self.status}`")
        self.status = "running"
        self.thread.start()

    def notify_exit(self, execution_exit: ThreadExecutionExit[T]) -> None:
        self.exit_emitter.fire(execution_exit)


@dataclass(frozen=True)
class ThreadExecutionRequest[T]:
    """
    It is better for `main_func` to get the `CancelToken` and
    check periodically `is_set`.
    """

    main_func: Callable[[CancelToken], T]

    @staticmethod
    def _solve_main_func(main_func: Callable[[CancelToken], T] | Callable[[], T]) -> Callable[[CancelToken], T]:
        """Wrap the function without the argument."""
        from inspect import signature, Parameter
        from functools import wraps

        sig = signature(main_func)
        params = list(sig.parameters.values())

        if len(params) == 0 or all(p.default is not Parameter.empty for p in params):
            original = cast(Callable[[], T], main_func)

            @wraps(original)
            def wrapper(cancel_token: CancelToken) -> T:
                return original()

            return cast(Callable[[CancelToken], T], wrapper)
        return cast(Callable[[CancelToken], T], main_func)

    @classmethod
    def from_any(
        cls,
        main_func: Callable[[CancelToken], T] | Callable[[], T],
    ) -> Self:
        main_func = cls._solve_main_func(main_func)
        return cls(main_func=main_func)


@dataclass(frozen=True)
class ThreadExecutionQuery:
    id: ThreadExecutionID | None = None
    statuses: tuple[ThreadExecutionStatus, ...] | None = None
    kind: str | None = None

    @classmethod
    def from_any(
        cls,
        id: ThreadExecutionID | None = None,
        statuses: ThreadExecutionStatus | Sequence[ThreadExecutionStatus] | None = None,
        kind: str | None = None,
    ) -> Self:
        if statuses is None:
            n_statuses = None
        elif isinstance(statuses, str):
            n_statuses = (cast(ThreadExecutionStatus, statuses),)
        else:
            n_statuses = tuple(statuses)
        return cls(id=id, statuses=n_statuses, kind=kind)
