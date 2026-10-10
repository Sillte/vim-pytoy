import threading

from pytoy.shared.timertask import TimerTask
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionManager, LLMSessionRequest


class RecordingDriver:
    def __init__(self) -> None:
        self.called = threading.Event()
        self.dispatch_thread = False

    def make_progress(self, execution_creator, llm_buffer_provider, user_prompt: str) -> None:
        self.dispatch_thread = TimerTask.is_dispatch_thread()
        self.called.set()


def test_make_progress_from_worker_is_dispatched_to_backend_thread() -> None:
    driver = RecordingDriver()
    session = LLMSessionHandler.create(
        LLMSessionRequest.from_any(driver=driver),
        manager=LLMSessionManager(),
    )
    worker_errors: list[Exception] = []

    def make_progress() -> None:
        try:
            session.make_progress("worker prompt")
        except Exception as error:
            worker_errors.append(error)

    worker = threading.Thread(target=make_progress)
    worker.start()
    worker.join(timeout=5)

    try:
        assert not worker.is_alive()
        assert worker_errors == []
        assert driver.called.wait(timeout=5)
        assert driver.dispatch_thread
    finally:
        session.terminate()
