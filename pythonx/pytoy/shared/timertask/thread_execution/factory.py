import uuid
from threading import Thread

from pytoy.contexts.core import GlobalCoreContext

from threading import Event 
from .models import ThreadExecution, ThreadExecutionRequest, ThreadExecutionExit
from .manager import ThreadExecutionManager
from pytoy.shared.lib.outcome import Success, Error

class ThreadExecutionFactory:
    def __init__(self, *, manager: ThreadExecutionManager | None = None):
        if manager is None:
            manager = GlobalCoreContext.get().thread_execution_manager
        self._manager: ThreadExecutionManager = manager

    def create(self, request: ThreadExecutionRequest) -> ThreadExecution: 
        id_ = str(uuid.uuid4())
        cancel_token = Event()

        def _run(event: Event):
            try:
                ret = request.main_func(event)
            except Exception as e:
                outcome = Error(e)
            else:
                outcome = Success(ret)
            exit_entity = ThreadExecutionExit(id=id_, outcome=outcome)
            self._manager.submit_exit_entity(exit_entity)

        thread = Thread(target=_run, daemon=True, args=(cancel_token,))
        execution = ThreadExecution(id=id_, thread=thread, cancel_token=cancel_token)
        return self._manager.register(execution)
         