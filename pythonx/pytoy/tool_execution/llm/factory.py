from pytoy_llm.activity_sinks import LoggerActivitySink
from pytoy_llm.task import TaskRequest, TaskSyncExecutor
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
        logger = request.logger
        if logger:
            activity_sink = LoggerActivitySink(request.logger)
        else:
            activity_sink = None
        task_request = TaskRequest(
            spec=request.task_spec,
            input=request.input,
            context_state=request.context_state,
            activity_sink=activity_sink,
        )

        def _main(_) -> TaskResult[T]:
            task_response = TaskSyncExecutor().execute(request=task_request)
            return task_response.result

        thread_request = ThreadExecutionRequest.from_any(_main)
        execution = LLMExecution.from_any(thread_request, llm_request=request)
        return execution
