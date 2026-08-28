from pytoy_llm.event_sinks import LoggerEventSink
from pytoy_llm.task import TaskExecutor, TaskRequest
from pytoy_llm.task.models import TaskResult

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.timertask.thread_execution import ThreadExecutionRequest

from .manager import LLMExecutionManager
from .models import LLMExecution, LLMExecutionRequest


class LLMExecutionFactory:
    def __init__(self, *, manager: LLMExecutionManager | None = None):
        if manager is None:
            manager = GlobalPytoyContext.get().llm_execution_manager
        self._manager = manager

    def create[T](self, request: LLMExecutionRequest[T]) -> LLMExecution[T]:
        task_request = TaskRequest(spec=request.task_spec, input=request.input, context_state=request.context_state)

        def _main(_) -> TaskResult[T]:
            logger = request.logger
            if logger:
                event_sink = LoggerEventSink(request.logger)
            else:
                event_sink = None
            task_response = TaskExecutor().execute(request=task_request, event_sink=event_sink)
            return task_response.result

        thread_request = ThreadExecutionRequest.from_any(_main)
        return LLMExecution.from_any(thread_request, llm_request=request)
