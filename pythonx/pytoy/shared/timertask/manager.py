import functools
from typing import Callable, cast

from pytoy.shared.lib.backend import can_use_vim
from pytoy.shared.timertask.domain import (
    OnErrorCallback,
    OnFinishCallback,
    OnTaskCallback,
    TaskName,
    TimerTaskImplProtocol,
)


def _wrap_to_one_argument_func[T, R](
    func: Callable[[], R] | Callable[[T], R],
) -> Callable[[T], R]:
    import inspect

    sig = inspect.signature(func)
    if len(sig.parameters) == 0:
        zero_arg_func = cast(Callable[[], R], func)

        @functools.wraps(zero_arg_func)
        def wrapper(_: T) -> R:
            return zero_arg_func()

        return wrapper
    if len(sig.parameters) == 1:
        return cast(Callable[[T], R], func)
    raise ValueError("Function must accept either zero or one argument.")


def get_timer_task_impl() -> TimerTaskImplProtocol:
    if can_use_vim():
        from pytoy.shared.timertask.impls.vim.timertask_impl import TimerTaskImplVim

        return TimerTaskImplVim()
    from pytoy.shared.timertask.impls.dummy import TimerTaskImplDummy

    return TimerTaskImplDummy()


class TimerTaskManager:
    def __init__(self, impl: TimerTaskImplProtocol | None = None) -> None:
        self.impl = impl or get_timer_task_impl()

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: OnFinishCallback | None = None,
        on_error: OnErrorCallback | None = None,
    ) -> TaskName:
        import inspect

        interval = int(interval)
        finish_callback = _wrap_to_one_argument_func(on_finish) if on_finish is not None else None
        error_callback = _wrap_to_one_argument_func(on_error) if on_error is not None else None

        if len(inspect.signature(func).parameters) != 0:
            raise ValueError("Task Callback must be without parameters.")

        return self.impl.register(func, interval, name, repeat, finish_callback, error_callback)

    def deregister(self, name: TaskName, *, strict: bool = False) -> None:
        self.impl.deregister(name, strict=strict)

    def is_registered(self, name: TaskName) -> bool:
        return self.impl.is_registered(name)

    def execute_oneshot(self, func: OnTaskCallback, interval: int = 100, name: TaskName | None = None) -> TaskName:
        return self.register(func, interval=interval, name=name, repeat=1)
