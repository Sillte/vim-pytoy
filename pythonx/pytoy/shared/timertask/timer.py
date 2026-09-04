from pytoy.shared.timertask.domain import (
    OnErrorCallback,
    OnFinishCallback,
    OnTaskCallback,
    TaskName,
    TimerTaskImplProtocol,
)
from pytoy.shared.timertask.manager import TimerTaskManager


class TimerTask:
    impl: None | TimerTaskImplProtocol = None
    manager: None | TimerTaskManager = None

    @classmethod
    def set_impl(cls, impl: TimerTaskImplProtocol) -> None:
        cls.impl = impl
        cls.manager = TimerTaskManager(impl)

    @classmethod
    def get_manager(cls) -> TimerTaskManager:
        if cls.manager is None:
            cls.manager = TimerTaskManager(cls.impl)
            cls.impl = cls.manager.impl
        return cls.manager

    @classmethod
    def get_impl(cls) -> "TimerTaskImplProtocol":
        return cls.get_manager().impl

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
