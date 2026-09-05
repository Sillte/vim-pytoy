import functools
import threading
from dataclasses import dataclass
from typing import Callable, cast

from pytoy.shared.lib.backend import can_use_vim
from pytoy.shared.lib.event import Disposable
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


@dataclass
class _ImplTask:
    impl_name: str
    deregister_requested: bool = False


class TimerTaskManager:
    def __init__(self, impl: TimerTaskImplProtocol | None = None) -> None:
        self.impl = impl or get_timer_task_impl()
        self._lock = threading.RLock()
        self._counter = 0
        self._tasks: dict[TaskName, _ImplTask] = {}
        self._impl_to_public: dict[TaskName, TaskName] = {}
        self._subscriptions: tuple[Disposable, Disposable] = (
            self.impl.on_registered.subscribe(self._on_impl_registered),
            self.impl.on_deregistered.subscribe(self._on_impl_deregistered),
        )

    def _on_impl_registered(self, impl_name: TaskName) -> None:
        with self._lock:
            public_name = self._impl_to_public.get(impl_name)
            if public_name is None:
                return
            task = self._tasks.get(public_name)
            if task is None:
                self.impl.deregister(impl_name)
                return

    def _on_impl_deregistered(self, impl_name: TaskName) -> None:
        with self._lock:
            public_name = self._impl_to_public.pop(impl_name, None)
            if public_name is not None:
                self._tasks.pop(public_name, None)

    def _allocate_names(self, requested_name: TaskName | None) -> tuple[TaskName, TaskName]:
        public_name = requested_name
        if public_name is None:
            self._counter += 1
            public_name = f"AUTONAME{self._counter}"
        with self._lock:
            if public_name in self._tasks:
                raise ValueError(f"Task {public_name!r} is already registered.")
            self._counter += 1
            impl_name = f"{public_name}_TimerTaskImpl_{self._counter}_{id(self)}"
            self._tasks[public_name] = _ImplTask(impl_name)
            self._impl_to_public[impl_name] = public_name
        return public_name, impl_name

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

        public_name, impl_name = self._allocate_names(name)
        try:
            self.impl.register(func, interval, impl_name, repeat, finish_callback, error_callback)
        except Exception:
            with self._lock:
                self._tasks.pop(public_name, None)
                self._impl_to_public.pop(impl_name, None)
            raise
        return public_name

    def deregister(self, name: TaskName, *, strict: bool = False) -> None:
        with self._lock:
            task = self._tasks.pop(name, None)
            if task is None:
                if strict:
                    raise KeyError(f"No timer task registered with name: '{name}'")
                return
            self._impl_to_public.pop(task.impl_name, None)
        self.impl.deregister(task.impl_name, strict=False)

    def is_registered(self, name: TaskName) -> bool:
        with self._lock:
            return name in self._tasks

    def execute_oneshot(self, func: OnTaskCallback, interval: int = 100, name: TaskName | None = None) -> TaskName:
        return self.register(func, interval=interval, name=name, repeat=1)
