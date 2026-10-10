from __future__ import annotations

import threading
from collections.abc import Callable
from functools import wraps

from .timertask import TimerTask


def is_backend_or_main_thread() -> bool:
    return threading.current_thread() is threading.main_thread() or TimerTask.is_dispatch_thread()


def assert_backend_or_main_thread() -> None:
    if not is_backend_or_main_thread():
        raise RuntimeError("This method must be called from the main thread or a TimerTask dispatch thread.")


def backend_or_main_thread_only[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        assert_backend_or_main_thread()
        return func(*args, **kwargs)

    return wrapper
