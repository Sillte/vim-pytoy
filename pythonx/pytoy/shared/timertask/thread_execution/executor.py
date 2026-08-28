from pytoy.contexts.core import GlobalCoreContext

from .factory import ThreadExecutionFactory
from .handler import ThreadExecutionHandler
from .manager import ThreadExecutionManager
from .models import ThreadExecutionHooks, ThreadExecutionRequest


class ThreadExecutor:
    def __init__(self, *, manager: ThreadExecutionManager | None = None):
        if manager is None:
            manager = GlobalCoreContext.get().thread_execution_manager
        self._manager: ThreadExecutionManager = manager
        self._factory = ThreadExecutionFactory(manager=self._manager)

    def execute(self, request: ThreadExecutionRequest, hooks: ThreadExecutionHooks) -> ThreadExecutionHandler:
        execution = self._factory.create(request)
        handler = ThreadExecutionHandler(id=execution.id, manager=self._manager)
        handler.start(hooks=hooks)
        return handler
