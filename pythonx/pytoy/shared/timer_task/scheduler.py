from pytoy.contexts.core import GlobalCoreContext
from pytoy.shared.timer_task.domain import (
    OnErrorCallback,
    OnFinishCallback,
    OnTaskCallback,
    TaskName,
)
from pytoy.shared.timer_task.manager import TimerTaskManager


def backend_thread_dispatch(func: OnTaskCallback, *, on_error: OnErrorCallback | None = None) -> None:
    """Schedule a callback on the dispatch thread of the context's TimerTaskManager."""
    GlobalCoreContext.get().timer_task_manager.register(func, interval=0, repeat=1, on_error=on_error)


class TimerTaskScheduler:
    def __init__(self, manager: TimerTaskManager | None = None) -> None:
        self._manager = manager if manager is not None else GlobalCoreContext.get().timer_task_manager

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: OnFinishCallback | None = None,
        on_error: OnErrorCallback | None = None,
    ) -> str:
        """Register a task and optionally repeat it.

        ``repeat=-1`` runs indefinitely. ``repeat=0`` and ``repeat=1`` both
        run the task once; positive values greater than one run it that many
        times.
        """
        return self._manager.register(func, interval, name, repeat, on_finish, on_error)

    def deregister(self, name: TaskName, *, strict: bool = False) -> None:
        self._manager.deregister(name, strict=strict)

    def is_registered(self, name: str) -> bool:
        return self._manager.is_registered(name)

    def is_dispatch_thread(self) -> bool:
        """Return whether the current thread executes TimerTaskScheduler callbacks."""
        return self._manager.is_dispatch_thread()

    def execute_oneshot(self, func: OnTaskCallback, interval: int = 100, name: str | None = None) -> TaskName:
        return self._manager.execute_oneshot(func, interval=interval, name=name)


if __name__ == "__main__":

    def hello():
        print("Hogege")

    TimerTaskScheduler().register(hello)
