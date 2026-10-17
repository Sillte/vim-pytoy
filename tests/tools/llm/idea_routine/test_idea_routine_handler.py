import threading
from concurrent.futures import Future
from types import SimpleNamespace
from typing import cast

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.task.models import FunctionInvocationSpec, TaskSpec

from pytoy.shared.lib.event import EventEmitter
from pytoy.shared.lib.outcome import Error, Success
from pytoy.tool_session.llm import LLMSessionHandler
from pytoy.tools.llm.idea_circulation import routines
from pytoy.tools.llm.idea_circulation.driver import IdeaCirculationDriver
from pytoy.tools.llm.idea_circulation.handler import IdeaCirculationHandler
from pytoy.tools.llm.idea_circulation.routines import ValueCycleRoutineHandler


class RecordingSessionHandler:
    def __init__(self) -> None:
        self._exit_emitter = EventEmitter[object]()
        self.task_requests = []
        self.task_started = threading.Event()
        self.task_future: Future = Future()

    @property
    def on_exit(self):
        return self._exit_emitter.event

    def execute_task(self, task_request) -> Future:
        self.task_requests.append(task_request)
        self.task_started.set()
        return self.task_future

    def terminate(self) -> None:
        pass


def make_handler(session_handler: RecordingSessionHandler, monkeypatch) -> IdeaCirculationHandler:
    invocation = FunctionInvocationSpec.from_any(lambda _: None)
    task_spec = TaskSpec.from_single_spec(invocation, output_type=type(None))
    monkeypatch.setattr(routines, "create_value_cycle_task_spec", lambda *_args, **_kwargs: task_spec)
    routine_handler = ValueCycleRoutineHandler.from_any(
        session_handler=cast(LLMSessionHandler, session_handler),
        idea_space=cast(IdeaSpace, object()),
        max_iteration=1,
    )
    return IdeaCirculationHandler(
        cast(LLMSessionHandler, session_handler),
        cast(IdeaCirculationDriver, object()),
        routine_handler,
    )


def test_idea_routine_waits_for_task_exit_before_finishing_iteration(monkeypatch) -> None:
    session_handler = RecordingSessionHandler()
    handler = make_handler(session_handler, monkeypatch)
    iteration_exited = threading.Event()
    handler._idea_routine._unit_handler.on_iteration_exit.subscribe(lambda _: iteration_exited.set())

    try:
        handler.start()
        assert session_handler.task_started.wait(timeout=5)
        assert not iteration_exited.wait(timeout=0.1)
        assert len(session_handler.task_requests) == 1
        assert session_handler.task_requests[0].input is None

        session_handler.task_future.set_result(SimpleNamespace(outcome=Success(None)))
        assert iteration_exited.wait(timeout=5)
    finally:
        if not session_handler.task_future.done():
            session_handler.task_future.set_result(SimpleNamespace(outcome=Success(None)))
        handler.terminate()


def test_idea_routine_propagates_task_start_failure_to_iteration(monkeypatch) -> None:
    session_handler = RecordingSessionHandler()
    handler = make_handler(session_handler, monkeypatch)
    iteration_exits = []
    iteration_exited = threading.Event()

    def record_exit(exit_entity) -> None:
        iteration_exits.append(exit_entity)
        iteration_exited.set()

    handler._idea_routine._unit_handler.on_iteration_exit.subscribe(record_exit)
    failure = RuntimeError("Task execution could not start")

    try:
        handler.start()
        assert session_handler.task_started.wait(timeout=5)
        session_handler.task_future.set_exception(failure)

        assert iteration_exited.wait(timeout=5)
        assert isinstance(iteration_exits[0].outcome, Error)
        assert iteration_exits[0].outcome.exception is failure
    finally:
        if not session_handler.task_future.done():
            session_handler.task_future.set_result(SimpleNamespace(outcome=Success(None)))
        handler.terminate()
