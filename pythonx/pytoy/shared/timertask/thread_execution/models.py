from __future__ import annotations
from typing import Callable, Any, cast, Literal, Self, Sequence, assert_never
from threading import Thread
from threading import Event as ThreadingEvent
from dataclasses import dataclass, field
import uuid

from pytoy.shared.lib.event import Event, EventEmitter

type ThreadExecutionID = str
type CancelToken = ThreadingEvent
type ThreadExecutionStatus = Literal["created", "running", "finished", "error"]
type ResultType = Literal["Finished", "Error"]


@dataclass(frozen=True)
class ThreadExecutionResult:
    id: ThreadExecutionID
    result_type: ResultType
    result: Any | None = None
    exception: Exception | None = None


@dataclass(frozen=True)
class ThreadExecutionHooks:
    on_finish: Callable[[Any], None]
    on_error: Callable[[Exception], None]

    @classmethod
    def from_any(
        cls, on_finish: Callable[[Any], None] | None = None, on_error: Callable[[Exception], None] | None = None
    ) -> Self:
        return cls(on_finish=(on_finish or (lambda _: None)), on_error=(on_error or (lambda _: None)))


@dataclass
class ThreadExecution:
    thread: Thread
    cancel_token: CancelToken
    id: ThreadExecutionID = field(default_factory=lambda: str(uuid.uuid4()))
    status: ThreadExecutionStatus = "created"
    hooks: ThreadExecutionHooks | None = None
    exit_emitter: EventEmitter[ThreadExecutionResult] = field(default_factory=EventEmitter)
    kind: str = "$default"

    @property
    def on_exit(self) -> Event:
        return self.exit_emitter.event

    def start(self, hooks: ThreadExecutionHooks) -> None:
        if self.status != "created":
            raise RuntimeError(f"When `start` is called, `status` must be `created`, but `{self.status}`")
        self.hooks = hooks
        self.status = "running"
        self.thread.start()

    def complete_from_result(self, result: ThreadExecutionResult) -> None:
        if self.hooks is None:
            raise RuntimeError("`self.hooks` is None. It is an implementation error.")
        hook_exception: Exception | None = None
        try:
            self._resolve_result(result)
        except Exception as e:
            hook_exception = e

        self.exit_emitter.fire(result)

        if hook_exception is not None:
            raise hook_exception

    def _resolve_result(self, result: ThreadExecutionResult) -> None:
        assert self.hooks is not None
        hooks = self.hooks
        match result.result_type:
            case "Finished":
                self.status = "finished"
                hooks.on_finish(result.result)
            case "Error":
                self.status = "error"
                if result.exception:
                    hooks.on_error(result.exception)
                else:
                    raise RuntimeError(f"`{result=}` does not have exception.")
            case _:
                assert_never(result.result_type)


@dataclass(frozen=True)
class ThreadExecutionRequest:
    """
    It is better for `main_func` to get the `CancelToken` and
    check periodically `is_set`.
    """

    main_func: Callable[[CancelToken], Any]

    @staticmethod
    def _solve_main_func(main_func: Callable[[CancelToken], Any] | Callable[[], Any]) -> Callable[[CancelToken], Any]:
        """Wrap the function without the argument."""
        from inspect import signature, Parameter
        from functools import wraps

        sig = signature(main_func)
        params = list(sig.parameters.values())

        if len(params) == 0 or all(p.default is not Parameter.empty for p in params):
            original = cast(Callable[[], Any], main_func)

            @wraps(original)
            def wrapper(cancel_token: CancelToken) -> Any:
                return original()

            return cast(Callable[[CancelToken], Any], wrapper)
        return cast(Callable[[CancelToken], Any], main_func)

    @classmethod
    def from_any(
        cls,
        main_func: Callable[[CancelToken], Any] | Callable[[], Any],
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
