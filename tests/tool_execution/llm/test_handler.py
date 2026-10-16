import threading
from concurrent.futures import Future

import pytest
from pytoy_llm.task.models import FunctionInvocationSpec, TaskSpec

from pytoy.shared.timertask import TimerTask
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

    future = handler.start(LLMExecutionHooks.from_any(on_result=on_result))

    assert isinstance(future, Future)
    assert finished.wait(5)
    exit_entity = future.result(timeout=5)
    assert exit_entity.id == handler.id
    assert exit_entity.outcome.value.output == 2
    assert [result for result in results] == [2]
    assert manager.get(handler.id) is None


def test_cancelling_future_does_not_cancel_execution() -> None:
    manager = LLMExecutionManager()
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    results = []

    def invoke(value: int) -> int:
        started.set()
        assert release.wait(5)
        return value + 1

    def on_result(result) -> None:
        results.append(result.output)
        finished.set()

    handler = LLMExecutionHandler.create(make_request(invoke), manager=manager)
    future = handler.start(LLMExecutionHooks.from_any(on_result=on_result))

    try:
        assert started.wait(5)
        assert future.cancel()
    finally:
        release.set()

    assert finished.wait(5)
    assert future.cancelled()
    assert results == [2]
    assert manager.get(handler.id) is None


def test_handler_can_be_created_and_started_on_backend_thread() -> None:
    manager = LLMExecutionManager()
    completed = threading.Event()
    errors = []
    results = []

    def on_result(result) -> None:
        results.append(result.output)
        completed.set()

    def start_execution() -> None:
        try:
            handler = LLMExecutionHandler.create(make_request(lambda value: value + 1), manager=manager)
            handler.start(LLMExecutionHooks.from_any(on_result=on_result))
        except Exception as error:
            errors.append(error)
            completed.set()

    TimerTask.register(start_execution, interval=0, repeat=1, on_error=errors.append)

    assert completed.wait(5)
    assert errors == []
    assert results == [2]


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

    future = handler.start(LLMExecutionHooks.from_any(on_exception=on_exception))

    assert finished.wait(5)
    exit_entity = future.result(timeout=5)
    assert exit_entity.id == handler.id
    assert exit_entity.outcome.exception is exceptions[0]
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], Exception)
    assert manager.get(handler.id) is None


def test_start_raises_startup_errors_synchronously() -> None:
    manager = LLMExecutionManager()
    handler = LLMExecutionHandler.create(make_request(lambda value: value + 1), manager=manager)

    def reject_start(_execution_id, _start) -> None:
        raise RuntimeError("startup failed")

    manager.start_execution = reject_start

    with pytest.raises(RuntimeError, match="startup failed"):
        handler.start()
