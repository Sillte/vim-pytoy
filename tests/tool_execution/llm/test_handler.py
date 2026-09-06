import threading

from pytoy_llm.task.models import FunctionInvocationSpec, TaskSpec

from pytoy.tool_execution.llm import (
    LLMExecutionHandler,
    LLMExecutionHooks,
    LLMExecutionQuery,
    LLMExecutionRequest,
)
from pytoy.tool_execution.llm.manager import LLMExecutionManager


def make_request(function):
    invocation_spec = FunctionInvocationSpec.from_any(function)
    task_spec = TaskSpec.from_single_spec(invocation_spec, output_type=int)
    return LLMExecutionRequest(task_spec=task_spec, input=1, kind="test")


def test_create_exposes_handler_and_query_before_start() -> None:
    manager = LLMExecutionManager()
    handler = LLMExecutionHandler.create(make_request(lambda value: value + 1), manager=manager)

    assert handler.status == "created"
    assert [item.id for item in LLMExecutionHandler.query(LLMExecutionQuery(kind="test"), manager=manager)] == [
        handler.id
    ]


def test_start_calls_result_hook_and_removes_finished_execution() -> None:
    manager = LLMExecutionManager()
    finished = threading.Event()
    results = []
    handler = LLMExecutionHandler.create(make_request(lambda value: value + 1), manager=manager)

    def on_result(result) -> None:
        results.append(result.output)
        finished.set()

    handler.start(LLMExecutionHooks.from_any(on_result=on_result))

    assert finished.wait(5)
    assert [result for result in results] == [2]
    assert manager.get(handler.id) is None


def test_start_calls_exception_hook_for_failed_invocation() -> None:
    manager = LLMExecutionManager()
    finished = threading.Event()
    exceptions = []

    def fail(_):
        raise ValueError("expected failure")

    def on_exception(exception) -> None:
        exceptions.append(exception)
        finished.set()

    handler = LLMExecutionHandler.create(make_request(fail), manager=manager)

    handler.start(LLMExecutionHooks.from_any(on_exception=on_exception))

    assert finished.wait(5)
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], Exception)
    assert manager.get(handler.id) is None
