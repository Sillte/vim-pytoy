from unittest.mock import patch

from pytoy.tool_session.llm import LLMSessionExit, LLMSessionQuery, LLMSessionRequest
from pytoy.tool_session.llm.manager import LLMSessionManager
from pytoy.tool_session.llm.models import LLMSession


class Driver:
    def make_progress(self, execution_creator, llm_buffer_provider, llm_message) -> None:
        pass


def make_session(kind: str = "$default") -> LLMSession:
    request = LLMSessionRequest.from_any(driver=Driver(), kind=kind)
    with patch("pytoy.tool_session.llm.models.TaskSessionHandler.create"):
        return LLMSession.from_request(request)


def test_sessions_are_selected_by_kind() -> None:
    chat = make_session("chat")
    circulation = make_session("circulation")
    manager = LLMSessionManager()
    manager.register(chat)
    manager.register(circulation)

    assert manager.select(LLMSessionQuery.from_any(kind="chat")) == [chat]
    assert manager.select(LLMSessionQuery.from_any(kind="circulation")) == [circulation]


def test_query_defaults_and_accepts_existing_positional_parameters() -> None:
    assert LLMSessionQuery.from_any().metadata is None
    query = LLMSessionQuery.from_any(None, "kind", {"key": "value"})
    assert query.kind == "kind"
    assert query.metadata == {"key": "value"}


def test_terminate_fires_exit_event_once() -> None:
    session = make_session()
    events = []
    session.on_exit.subscribe(events.append)

    session.terminate()
    session.terminate()

    assert len(events) == 1
    assert isinstance(events[0], LLMSessionExit)
