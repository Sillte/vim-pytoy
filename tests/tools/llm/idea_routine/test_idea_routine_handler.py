import threading

from pytoy.shared.lib.event import EventEmitter
from pytoy.tools.llm.idea_routine.handler import IdeaRoutineHandler


class RecordingSessionHandler:
    def __init__(self) -> None:
        self._exit_emitter = EventEmitter[object]()
        self.prompts: list[str] = []
        self.progress_started = threading.Event()

    @property
    def on_exit(self):
        return self._exit_emitter.event

    def make_progress(self, user_prompt: str) -> None:
        self.prompts.append(user_prompt)
        self.progress_started.set()

    def terminate(self) -> None:
        pass


def test_idea_routine_starts_progress_through_session_handler() -> None:
    session_handler = RecordingSessionHandler()
    handler = IdeaRoutineHandler(session_handler, object())

    try:
        handler.start()
        assert session_handler.progress_started.wait(timeout=5)
        assert session_handler.prompts == ["NON-USED INPUT"]
    finally:
        handler.terminate()
