import threading
from concurrent.futures import Future
from types import SimpleNamespace
from typing import cast

from pytoy.shared.lib.event import EventEmitter
from pytoy.shared.lib.outcome import Error, Success
from pytoy.tool_session.llm import LLMSessionHandler
from pytoy.tools.llm.idea_routine.driver import IdeaRoutineDriver
from pytoy.tools.llm.idea_routine.handler import IdeaRoutineHandler


class RecordingSessionHandler:
    def __init__(self) -> None:
        self._exit_emitter = EventEmitter[object]()
        self.messages: list[None] = []
        self.progress_started = threading.Event()
        self.progress_future: Future = Future()

    @property
    def on_exit(self):
        return self._exit_emitter.event

    def make_progress(self) -> Future:
        self.messages.append(None)
        self.progress_started.set()
        return self.progress_future

    def terminate(self) -> None:
        pass


def test_idea_routine_waits_for_progress_exit_before_finishing_iteration() -> None:
    session_handler = RecordingSessionHandler()
    handler = IdeaRoutineHandler(cast(LLMSessionHandler, session_handler), cast(IdeaRoutineDriver, object()))
    iteration_exited = threading.Event()
    handler._routine_unit_handler.on_iteration_exit.subscribe(lambda _: iteration_exited.set())

    try:
        handler.start()
        assert session_handler.progress_started.wait(timeout=5)
        assert not iteration_exited.wait(timeout=0.1)
        assert session_handler.messages == [None]

        session_handler.progress_future.set_result(SimpleNamespace(outcome=Success(None)))
        assert iteration_exited.wait(timeout=5)
    finally:
        if not session_handler.progress_future.done():
            session_handler.progress_future.set_result(SimpleNamespace(outcome=Success(None)))
        handler.terminate()


def test_idea_routine_propagates_execution_failure_to_iteration() -> None:
    session_handler = RecordingSessionHandler()
    handler = IdeaRoutineHandler(cast(LLMSessionHandler, session_handler), cast(IdeaRoutineDriver, object()))
    iteration_exits = []
    iteration_exited = threading.Event()

    def record_exit(exit_entity) -> None:
        iteration_exits.append(exit_entity)
        iteration_exited.set()

    handler._routine_unit_handler.on_iteration_exit.subscribe(record_exit)
    failure = RuntimeError("LLM execution failed")

    try:
        handler.start()
        assert session_handler.progress_started.wait(timeout=5)
        session_handler.progress_future.set_result(SimpleNamespace(outcome=Error(failure)))

        assert iteration_exited.wait(timeout=5)
        assert iteration_exits[0].outcome.exception is failure
    finally:
        if not session_handler.progress_future.done():
            session_handler.progress_future.set_result(SimpleNamespace(outcome=Success(None)))
        handler.terminate()
