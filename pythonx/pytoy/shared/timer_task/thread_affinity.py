from __future__ import annotations

import threading
from collections.abc import Callable
from functools import wraps

from pytoy.contexts.core import GlobalCoreContext


def is_backend_or_main_thread() -> bool:
    manager = GlobalCoreContext.get().timer_task_manager
    return threading.current_thread() is threading.main_thread() or manager.is_dispatch_thread()


def assert_backend_or_main_thread() -> None:
    if not is_backend_or_main_thread():
        raise RuntimeError("This method must be called from the main thread or a TimerTaskScheduler dispatch thread.")


def backend_or_main_thread_only[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        assert_backend_or_main_thread()
        return func(*args, **kwargs)

    return wrapper
