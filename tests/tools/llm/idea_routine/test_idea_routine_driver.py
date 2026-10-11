from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMMessage, LLMRequest
from pytoy_llm.task.models import ExecutionContext

from pytoy.tool_session.llm import LLMMessageLike
from pytoy.tools.llm.idea_routine import driver as driver_module
from pytoy.tools.llm.idea_routine.driver import _make_task_spec


def test_idea_routine_uses_only_current_message_not_session_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(driver_module, "_construct_system_prompt", lambda **_: "system")
    monkeypatch.setattr(driver_module, "IdeaTool", SimpleNamespace(from_any=lambda **_: SimpleNamespace(tools=[])))
    monkeypatch.setattr(
        driver_module,
        "WorkspaceExplorer",
        SimpleNamespace(from_any=lambda **_: SimpleNamespace(tools=[])),
    )
    monkeypatch.setattr(driver_module, "InvocationHooks", SimpleNamespace(from_any=lambda **_: None))
    monkeypatch.setattr(
        driver_module,
        "ValuableDemandProviderTool",
        SimpleNamespace(from_any=lambda *_: SimpleNamespace(tools=[])),
    )
    monkeypatch.setattr(
        driver_module,
        "AgentInvocationSpec",
        SimpleNamespace(from_any=lambda **kwargs: captured.update(kwargs) or "agent-spec"),
    )
    monkeypatch.setattr(driver_module, "TaskSpec", SimpleNamespace(from_specs=lambda specs: specs))

    result = _make_task_spec(cast(IdeaSpace, SimpleNamespace(root_folder_path=tmp_path)))
    context_message = LLMMessage.from_prompt(user="old session message")
    current_message = LLMMessage.from_prompt(user="current message")
    context = ExecutionContext(llm_param=None, connection=None, llm_messages=[context_message])
    create_request = cast(Callable[[LLMMessageLike | None, ExecutionContext], LLMRequest], captured["create_request"])

    request = create_request(current_message, context)
    request_without_new_message = create_request(None, context)

    assert result == ["agent-spec"]
    assert request.messages == [current_message]
    assert request_without_new_message.messages == []
    assert request.system_prompt is not None
