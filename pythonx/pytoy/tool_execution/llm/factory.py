import logging
from typing import assert_never

from pytoy_llm.activity_sinks import LoggerActivitySink
from pytoy_llm.task import TaskRequest
from pytoy_llm.task.execution import TaskExecutionHandler
from pytoy_llm.task.execution.models import TaskExecutionExit
from pytoy_llm.task.shared.outcome import Error as TaskError
from pytoy_llm.task.shared.outcome import Success as TaskSuccess

from pytoy.shared.lib.event import EventEmitter
from pytoy.shared.lib.outcome import Error, Success, is_error, is_success
from pytoy.shared.timertask import backend_thread_dispatch
from pytoy.tool_execution.llm.models import LLMExecutionExit, LLMExecutionKind, LLMExecutionResult

from .logger import get_llm_logger
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
        logger = request.logger or get_llm_logger()
        activity_sink = request.activity_sink or LoggerActivitySink(logger)

        task_request = TaskRequest(
            spec=request.task_spec,
            input=request.input,
            context_state=request.context_state,
            activity_sink=activity_sink,
        )
        task_handler = TaskExecutionHandler.create(task_request)
        logger.info("execution.created kind=%s, id=%s", request.kind, request)
        return self.create_from_task_handler(task_handler, request.kind, logger=logger)

    def create_from_task_handler[T](
        self,
        task_handler: TaskExecutionHandler[T],
        kind: LLMExecutionKind,
        logger: logging.Logger | None = None,
    ) -> LLMExecution[T]:
        if task_handler.status != "created":
            raise ValueError(f"Only `created` task_handler is accepted, but `{task_handler.status=}`")
        exit_emitter = EventEmitter()
        execution = LLMExecution(kind=kind, task_handler=task_handler, exit_emitter=exit_emitter)

        logger = logger or get_llm_logger()

        def _dispatch_exit(execution_exit: LLMExecutionExit[T]) -> None:
            if is_success(execution_exit.outcome):
                logger.info("execution.succeeded id=%s kind=%s", execution.id, kind)
            else:
                exception = execution_exit.outcome.exception if is_error(execution_exit.outcome) else None
                logger.error("execution.failed id=%s kind=%s exception=%r", execution.id, kind, exception)
            backend_thread_dispatch(lambda: execution.exit_emitter.fire(execution_exit))

        execution.task_handler.on_exit.map(transform).once().subscribe(_dispatch_exit)
        return execution
