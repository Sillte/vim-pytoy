from typing import assert_never

from pytoy_llm.activity_sinks import LoggerActivitySink
from pytoy_llm.task import TaskRequest
from pytoy_llm.task.execution import TaskExecutionHandler
from pytoy_llm.task.execution.models import TaskExecutionExit
from pytoy_llm.task.shared.outcome import Error as TaskError
from pytoy_llm.task.shared.outcome import Success as TaskSuccess

from pytoy.shared.lib.event import EventEmitter
from pytoy.shared.lib.outcome import Error, Success
from pytoy.shared.timertask import backend_thread_dispatch
from pytoy.tool_execution.llm.models import LLMExecutionExit, LLMExecutionResult

from .models import LLMExecution, LLMExecutionRequest


def transform[T](task_exit: TaskExecutionExit[T]) -> LLMExecutionExit[T]:
    task_outcome = task_exit.outcome
    match task_outcome:
        case TaskSuccess(value):
            result = LLMExecutionResult(task_result=value)
            outcome = Success(result)
        case TaskError(exception):
            outcome = Error(exception)
        case _:
            assert_never(task_outcome)
    return LLMExecutionExit(id=task_exit.id, outcome=outcome)


class LLMExecutionFactory:
    def __init__(self) -> None:
        pass

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
        task_handler = TaskExecutionHandler.create(task_request)

        exit_emitter = EventEmitter()

        execution = LLMExecution(request=request, task_handler=task_handler, exit_emitter=exit_emitter)

        execution.task_handler.on_exit.map(transform).once().subscribe(
            lambda execution_exit: backend_thread_dispatch(lambda: execution.exit_emitter.fire(execution_exit))
        )
        return execution
