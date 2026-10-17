import threading
from concurrent.futures import Future
from typing import cast

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMTokens
from pytoy_llm.task.models import FunctionInvocationSpec, TaskSpec

from pytoy.shared.lib.event import EventEmitter
from pytoy.tool_session.llm import LLMSessionHandler
from pytoy.tools.llm.idea_circulation import routines
from pytoy.tools.llm.idea_circulation.driver import IdeaCirculationDriver
from pytoy.tools.llm.idea_circulation.handler import IdeaCirculationHandler
from pytoy.tools.llm.idea_circulation.routines import ValueCycleRoutineHandler
from pytoy.tools.llm.idea_circulation.statuses import IdeaCirculationStatus


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
        status=IdeaCirculationStatus(workspace_name=None, value_cycle_working_status="idle"),
        max_iteration=1,
    )
    return IdeaCirculationHandler(
        cast(LLMSessionHandler, session_handler),
        cast(IdeaCirculationDriver, object()),
        routine_handler,
    )


def test_idea_circulation_status_aggregates_tokens() -> None:
    status = IdeaCirculationStatus(workspace_name=None, value_cycle_working_status="idle")

    status.update_tokens(LLMTokens(prompt=3, completion=4, total=7, cache_read=1, cache_write=2))
    status.update_tokens(LLMTokens(prompt=5, completion=6, total=11, cache_read=2, cache_write=3))

    assert status.llm_tokens.prompt == 8
    assert status.llm_tokens.completion == 10
    assert status.llm_tokens.total == 18
    assert status.llm_tokens.cache_read == 3
    assert status.llm_tokens.cache_write == 5
