from typing import Self

from pytoy.contexts.core import GlobalCoreContext
from. models import  ThreadExecutionID, ThreadExecutionStatus, ThreadExecutionRequest, ThreadExecutionHooks
from .manager import ThreadExecutionManager
from .factory import ThreadExecutionFactory


class ThreadExecutionHandler:
    def __init__(self, id: ThreadExecutionID, manager: ThreadExecutionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    def from_request(cls, request: ThreadExecutionRequest, hooks: ThreadExecutionHooks, *, manager: ThreadExecutionManager | None = None) -> Self:
        if manager is None: 
             manager = GlobalCoreContext.get().thread_execution_manager
        factory = ThreadExecutionFactory(manager=manager)
        execution = factory.create(request, hooks)
        return cls(id=execution.id, manager=manager)

    @property
    def id(self):
        return self._id

    @property
    def status(self) -> ThreadExecutionStatus | None:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            return None
        return execution.status

    def execute(self) -> None:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"Already `execution` does not exit; {self._id=}")
        execution.start()

    def cancel(self) -> None:
        execution = self._manager.get_execution(self._id)
        if execution is None:
            raise ValueError(f"Already `execution` does not exit; {self._id=}")
        execution.cancel_token.set()
