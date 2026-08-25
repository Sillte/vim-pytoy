import uuid
from threading import Thread

from pytoy.contexts.core import GlobalCoreContext

from threading import Event 
from .models import ThreadExecution, ThreadExecutionHooks, ThreadExecutionRequest, ThreadExecutionResult
from .manager import ThreadExecutionManager

class ThreadExecutionFactory:
    def __init__(self, *, manager: ThreadExecutionManager | None = None):
        if manager is None:
            manager = GlobalCoreContext.get().thread_execution_manager
        self._manager: ThreadExecutionManager = manager

    def create(self, request: ThreadExecutionRequest, hooks:ThreadExecutionHooks) -> ThreadExecution: 
        id_ = str(uuid.uuid4())
        cancel_token = Event()

        def _run(event: Event):
            try:
                ret = request.main_func(event)
            except Exception as e:
                result = ThreadExecutionResult(id=id_, result_type="Error", exception=e)
            else:
                result = ThreadExecutionResult(id=id_, result_type="Finished", result=ret)
            self._manager.submit_result(result)

        thread = Thread(target=_run, daemon=True, args=(cancel_token,))
        execution = ThreadExecution(id=id_, thread=thread, cancel_token=cancel_token)
        return self._manager.register(execution, hooks=hooks)
         