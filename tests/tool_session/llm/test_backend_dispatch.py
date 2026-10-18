import threading
from typing import Any, cast

import pytest
from pytoy_llm.models import LLMMessage
from pytoy_llm.task.execution import TaskExecutionHandler
from pytoy_llm.task.models import FunctionInvocationSpec, TaskContextState, TaskRequest, TaskSpec

from pytoy.contexts.core import GlobalCoreContext
from pytoy.shared.lib.event import EventEmitter
from pytoy.shared.lib.outcome import Error
from pytoy.shared.timertask import TimerTask
from pytoy.shared.timertask.domain import OnTaskCallback, TaskName
from pytoy.shared.timertask.impls.dummy import TimerTaskImplDummy
from pytoy.shared.timertask.manager import TimerTaskManager
from pytoy.tool_execution.llm import LLMExecutionExit, LLMExecutionHandler
from pytoy.tool_execution.llm.manager import LLMExecutionManager
from pytoy.tool_execution.llm.models import LLMExecution
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionManager, LLMSessionRequest
from pytoy.tool_session.llm.handler import _SingleExecutionCreator


@pytest.fixture
def task_request() -> TaskRequest[int]:
    invocation_spec = FunctionInvocationSpec.from_any(lambda value: value + 1)
    task_spec = TaskSpec.from_single_spec(invocation_spec, output_type=int)
    return TaskRequest(spec=task_spec, input=1)


@pytest.fixture
def install_timer_task_impl():
    context = GlobalCoreContext.get()
    previous_manager = context.__dict__.get("timer_task_manager")

    def install(impl):
        context.timer_task_manager = TimerTaskManager(impl)
        return impl

    yield install
    if previous_manager is None:
        context.__dict__.pop("timer_task_manager", None)
    else:
        context.timer_task_manager = previous_manager


@pytest.fixture
def dummy_impl(install_timer_task_impl):
    return install_timer_task_impl(TimerTaskImplDummy())


class FailingTimerTaskImpl(TimerTaskImplDummy):
    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
    ) -> TaskName:
        raise RuntimeError("dispatch failed")


class RecordingTaskExecutionHandler:
    id = "execution-id"
    on_cancel = EventEmitter().event


def make_execution_handler() -> tuple[LLMExecutionHandler[Any], EventEmitter[LLMExecutionExit[Any]]]:
    exit_emitter = EventEmitter[LLMExecutionExit[Any]]()
    execution = LLMExecution(
        kind="test",
        task_handler=cast(TaskExecutionHandler[Any], RecordingTaskExecutionHandler()),
        exit_emitter=exit_emitter,
    )
    manager = LLMExecutionManager()
    manager.register(execution)
    handler = LLMExecutionHandler(id=execution.id, manager=manager)
    return handler, exit_emitter


def make_execution_exit() -> LLMExecutionExit[Any]:
    return LLMExecutionExit(id="execution-id", outcome=Error(RuntimeError("execution failed")))


def set_recording_execution_handler(session: LLMSessionHandler, execution_handler: LLMExecutionHandler[Any]) -> None:
    def create_handler(_: TaskRequest) -> LLMExecutionHandler[Any]:
        return execution_handler

    setattr(session, "make_execution_handler", create_handler)


def test_single_execution_creator_enforces_exactly_one_synchronous_call(task_request: TaskRequest[int]) -> None:
    execution_handler, _ = make_execution_handler()

    def create_handler(_: TaskRequest) -> LLMExecutionHandler[Any]:
        return execution_handler

    creator = _SingleExecutionCreator(create_handler, lambda _: None)

    assert creator(task_request) is execution_handler
    creator.validate()
    with pytest.raises(RuntimeError):
        creator(task_request)

    missing_creator = _SingleExecutionCreator(create_handler, lambda _: None)
    with pytest.raises(RuntimeError):
        missing_creator.validate()
    with pytest.raises(RuntimeError):
        missing_creator(task_request)


class RecordingDriver:
    def __init__(self, task_request: TaskRequest[Any]) -> None:
        self.task_request = task_request
        self.called = threading.Event()
        self.dispatch_thread = False
        self.execution_handler = None
        self.llm_message = None

    def make_progress(self, execution_creator, llm_buffer_provider, llm_message) -> None:
        self.dispatch_thread = TimerTask.is_dispatch_thread()
        self.llm_message = llm_message
        self.execution_handler = execution_creator(self.task_request)
        self.called.set()


def test_execute_task_from_worker_uses_session_context_and_returns_exit(
    dummy_impl, task_request: TaskRequest[int]
) -> None:
    task_context = TaskContextState()
    session = LLMSessionHandler.create(
        LLMSessionRequest.from_any(driver=RecordingDriver(task_request), task_context=task_context),
        manager=LLMSessionManager(),
    )
    futures = []
    errors: list[Exception] = []

    def execute_task() -> None:
        try:
            futures.append(session.execute_task(task_request))
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=execute_task)
    worker.start()
    worker.join(timeout=5)

    try:
        assert not worker.is_alive()
        assert errors == []
        assert len(futures) == 1

        exit_entity = futures[0].result(timeout=5)
        assert exit_entity.outcome.value.output == 2
        session_model = session._manager.get(session._id)
        assert session_model is not None
        task_session = session_model.task_session_handler
        task_record = next(record for record in task_session.records if record.id == exit_entity.id)
        assert task_record.request.context_state is task_context
        assert task_record.status == "finished"
    finally:
        session.terminate()


def test_make_progress_raises_when_dispatch_registration_fails(
    install_timer_task_impl, task_request: TaskRequest[int]
) -> None:
    install_timer_task_impl(FailingTimerTaskImpl())
    session = LLMSessionHandler.create(
        LLMSessionRequest.from_any(driver=RecordingDriver(task_request)),
        manager=LLMSessionManager(),
    )

    try:
        with pytest.raises(RuntimeError, match="dispatch failed"):
            session.make_progress("prompt")
    finally:
        session.terminate()


def test_make_progress_future_fails_when_driver_skips_execution_creation(dummy_impl) -> None:
    class MissingExecutionDriver:
        def make_progress(self, execution_creator, llm_buffer_provider, llm_message) -> None:
            pass

    session = LLMSessionHandler.create(
        LLMSessionRequest.from_any(driver=MissingExecutionDriver()),
        manager=LLMSessionManager(),
    )

    try:
        future = session.make_progress("prompt")
        with pytest.raises(RuntimeError, match="must create exactly one"):
            future.result(timeout=5)
    finally:
        session.terminate()


def test_make_progress_always_dispatches_and_future_waits_for_execution_exit(
    dummy_impl, task_request: TaskRequest[int]
) -> None:
    driver = RecordingDriver(task_request)
    session = LLMSessionHandler.create(
        LLMSessionRequest.from_any(driver=driver),
        manager=LLMSessionManager(),
    )
    execution_handler, exit_emitter = make_execution_handler()
    set_recording_execution_handler(session, execution_handler)

    llm_message = LLMMessage.from_prompt(user="main-thread prompt")

    try:
        future = session.make_progress(llm_message)
        assert driver.called.wait(timeout=5)
        assert driver.llm_message is llm_message
        assert driver.dispatch_thread
        assert driver.execution_handler is execution_handler
        assert not future.done()

        exit_entity = make_execution_exit()
        exit_emitter.fire(exit_entity)
        assert future.result(timeout=1) is exit_entity
    finally:
        session.terminate()


def test_make_progress_allows_a_run_without_a_new_message(dummy_impl, task_request: TaskRequest[int]) -> None:
    driver = RecordingDriver(task_request)
    session = LLMSessionHandler.create(
        LLMSessionRequest.from_any(driver=driver),
        manager=LLMSessionManager(),
    )
    execution_handler, exit_emitter = make_execution_handler()
    set_recording_execution_handler(session, execution_handler)

    try:
        future = session.make_progress()
        assert driver.called.wait(timeout=5)
        assert driver.llm_message is None

        exit_entity = make_execution_exit()
        exit_emitter.fire(exit_entity)
        assert future.result(timeout=1) is exit_entity
    finally:
        session.terminate()


def test_make_progress_from_worker_returns_future_and_dispatches_to_backend_thread(
    dummy_impl, task_request: TaskRequest[int]
) -> None:
    driver = RecordingDriver(task_request)
    session = LLMSessionHandler.create(
        LLMSessionRequest.from_any(driver=driver),
        manager=LLMSessionManager(),
    )
    execution_handler, exit_emitter = make_execution_handler()
    set_recording_execution_handler(session, execution_handler)
    futures = []
    worker_errors: list[Exception] = []

    def make_progress() -> None:
        try:
            futures.append(session.make_progress("worker prompt"))
        except Exception as error:
            worker_errors.append(error)

    worker = threading.Thread(target=make_progress)
    worker.start()
    worker.join(timeout=5)

    try:
        assert not worker.is_alive()
        assert worker_errors == []
        assert len(futures) == 1
        assert driver.called.wait(timeout=5)
        assert driver.dispatch_thread
        assert not futures[0].done()

        exit_entity = make_execution_exit()
        exit_emitter.fire(exit_entity)
        assert futures[0].result(timeout=1) is exit_entity
    finally:
        session.terminate()
