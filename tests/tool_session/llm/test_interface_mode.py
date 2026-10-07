from unittest.mock import patch

from pytoy.tool_session.llm import LLMSessionExit, LLMSessionInterfaceMode, LLMSessionQuery, LLMSessionRequest
from pytoy.tool_session.llm.manager import LLMSessionManager
from pytoy.tool_session.llm.models import LLMSession


class Driver:
    def make_progress(self, execution_creator, llm_buffer_provider, user_prompt: str) -> None:
        pass


def make_session(interface: LLMSessionInterfaceMode = "interactive") -> LLMSession:
    request = LLMSessionRequest.from_any(driver=Driver(), interface=interface)
    with patch("pytoy.tool_session.llm.models.TaskSessionHandler.create"):
        return LLMSession.from_request(request)


def test_interface_mode_is_preserved_and_used_for_selection() -> None:
    interactive = make_session("interactive")
    autonomous = make_session("autonomous")
    manager = LLMSessionManager()
    manager.register(interactive)
    manager.register(autonomous)

    assert interactive.interface == "interactive"
    assert autonomous.interface == "autonomous"
    assert manager.select(LLMSessionQuery.from_any(interface="interactive")) == [interactive]
    assert manager.select(LLMSessionQuery.from_any(interface="autonomous")) == [autonomous]


def test_interface_mode_defaults_to_interactive() -> None:
    session = make_session()

    assert session.interface == "interactive"
    assert LLMSessionQuery.from_any().interface is None
    assert LLMSessionQuery.from_any(None, "kind", {"key": "value"}).kind == "kind"


def test_terminate_fires_exit_event_once() -> None:
    session = make_session()
    events = []
    session.on_exit.subscribe(events.append)

    session.terminate()
    session.terminate()

    assert len(events) == 1
    assert isinstance(events[0], LLMSessionExit)
