from pytoy.contexts.core import GlobalCoreContext
from pytoy.shared.timertask.domain import (
    OnErrorCallback,
    OnFinishCallback,
    OnTaskCallback,
    TaskName,
)
from pytoy.shared.timertask.manager import TimerTaskManager


class TimerTask:
    @classmethod
    def get_manager(cls) -> TimerTaskManager:
        return GlobalCoreContext.get().timer_task_manager

    @classmethod
    def register(
        cls,
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
        return cls.get_manager().register(func, interval, name, repeat, on_finish, on_error)

    @classmethod
    def deregister(cls, name: TaskName, *, strict: bool = False):
        cls.get_manager().deregister(name, strict=strict)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return cls.get_manager().is_registered(name)

    @classmethod
    def execute_oneshot(cls, func, interval: int = 100, name: str | None = None) -> TaskName:
        return cls.get_manager().execute_oneshot(func, interval=interval, name=name)


if __name__ == "__main__":

    def hello():
        print("Hogege")

    TimerTask.register(hello)
