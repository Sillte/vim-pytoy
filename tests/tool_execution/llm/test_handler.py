import threading
from concurrent.futures import Future
from typing import cast

import pytest
from pytoy_llm.task.models import FunctionInvocationSpec, TaskSpec

from pytoy.shared.lib.outcome import is_error
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
    exits = []
    handler = LLMExecutionHandler.create(make_request(lambda value: value + 1), manager=manager)

    def on_result(result) -> None:
        results.append(result.output)
        finished.set()

    future = handler.start(LLMExecutionHooks.from_any(on_result=on_result, on_exit=exits.append))

    assert isinstance(future, Future)
    assert finished.wait(5)
    exit_entity = future.result(timeout=5)
    assert exit_entity.id == handler.id
    assert not is_error(exit_entity.outcome)
    assert exit_entity.outcome.value.output == 2
    assert [result for result in results] == [2]
    assert exits == [exit_entity]
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
    exits = []

    def fail(_):
        raise ValueError("expected failure")

    def on_exception(exception) -> None:
        exceptions.append(exception)
        finished.set()

    handler = LLMExecutionHandler.create(make_request(fail), manager=manager)

    future = handler.start(LLMExecutionHooks.from_any(on_exception=on_exception, on_exit=exits.append))

    assert finished.wait(5)
    exit_entity = future.result(timeout=5)
    assert exit_entity.id == handler.id
    assert is_error(exit_entity.outcome)
    assert exit_entity.outcome.exception is exceptions[0]
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], Exception)
    assert exits == [exit_entity]
    assert manager.get(handler.id) is None


def test_execute_returns_future_when_called_from_worker_thread() -> None:
    manager = LLMExecutionManager()
    completed = threading.Event()
    futures = []
    errors = []

    def call_execute() -> None:
        try:
            futures.append(
                LLMExecutionHandler.execute(
                    make_request(lambda value: value + 1),
                    hooks=LLMExecutionHooks.from_any(on_result=lambda _: completed.set()),
                    manager=manager,
                )
            )
        except Exception as error:
            errors.append(error)

    caller = threading.Thread(target=call_execute)
    caller.start()
    caller.join(timeout=5)

    assert not caller.is_alive()
    assert errors == []
    assert len(futures) == 1
    future = futures[0]
    assert isinstance(future, Future)
    assert completed.wait(5)
    exit_entity = future.result(timeout=1)
    assert exit_entity.outcome.value.output == 2
    assert manager.get(exit_entity.id) is None


def test_execute_returns_exit_for_failed_invocation() -> None:
    manager = LLMExecutionManager()
    completed = threading.Event()
    exceptions = []

    def fail(_):
        raise ValueError("expected failure")

    def on_exception(exception) -> None:
        exceptions.append(exception)
        completed.set()

    future = LLMExecutionHandler.execute(
        make_request(fail),
        hooks=LLMExecutionHooks.from_any(on_exception=on_exception),
        manager=manager,
    )

    assert completed.wait(5)
    exit_entity = future.result(timeout=1)
    assert is_error(exit_entity.outcome)
    assert exit_entity.outcome.exception is exceptions[0]
    assert len(exceptions) == 1
    assert manager.get(exit_entity.id) is None


def test_execute_sets_future_exception_when_hook_setup_fails() -> None:
    manager = LLMExecutionManager()

    class FailingHooks:
        @property
        def on_exit(self):
            return lambda _: None

        @property
        def on_result(self):
            raise RuntimeError("hook setup failed")

        @property
        def on_exception(self):
            return lambda _: None

    hooks = cast(LLMExecutionHooks[int], FailingHooks())
    future = LLMExecutionHandler.execute(make_request(lambda value: value + 1), hooks=hooks, manager=manager)

    with pytest.raises(RuntimeError, match="hook setup failed"):
        future.result(timeout=5)
