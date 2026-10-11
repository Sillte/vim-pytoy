import re
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, cast

import pytest
from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMMessage, LLMParam, LLMRequest, UsageLimit
from pytoy_llm.task.models import ExecutionContext

from pytoy.tool_session.llm import LLMMessageLike
from pytoy.tools.llm.idea_chat import driver as driver_module
from pytoy.tools.llm.idea_chat.buffer_codec import LLMBufferCodec
from pytoy.tools.llm.idea_chat.driver import (
    LLM_CONFIGURATION_FILENAME,
    IdeaChatDriver,
    LLMConfiguration,
    _make_task_spec,
)
from pytoy.tools.llm.idea_chat.messages_codec import LLMMessagesCodec


def _make_driver(meta_folder: Path) -> IdeaChatDriver:
    driver = object.__new__(IdeaChatDriver)
    driver._idea_space = cast(IdeaSpace, SimpleNamespace(root_space=SimpleNamespace(space_meta_folder=meta_folder)))
    return driver


def test_missing_configuration_uses_defaults(tmp_path: Path):
    driver = _make_driver(tmp_path)

    assert driver.read_configuration_file() == LLMConfiguration()


def test_open_configuration_file_creates_commented_yaml_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    opened: dict[str, object] = {}
    monkeypatch.setattr(
        driver_module,
        "PytoyWindow",
        SimpleNamespace(open=lambda path, **kwargs: opened.update(path=path, **kwargs)),
    )
    driver = _make_driver(tmp_path)

    driver.open_configuration_file()

    config_path = tmp_path / LLM_CONFIGURATION_FILENAME
    assert config_path.exists()
    assert "# llm_param:" in config_path.read_text(encoding="utf8")
    assert opened == {"path": config_path, "param": "vertical"}


def test_configuration_is_loaded_and_validated(tmp_path: Path):
    config_path = tmp_path / LLM_CONFIGURATION_FILENAME
    config_path.write_text(
        "llm_param:\n  reasoning_effort: medium\n  max_tokens: 4096\n"
        "usage_limit:\n  max_total_tokens: 50000\n  max_requests: 20\n"
        "connection_name: local\n",
        encoding="utf8",
    )

    config = _make_driver(tmp_path).read_configuration_file()

    assert config.llm_param == LLMParam(reasoning_effort="medium", max_tokens=4096)
    assert config.usage_limit == UsageLimit(max_total_tokens=50000, max_requests=20)
    assert config.connection_name == "local"


def test_invalid_configuration_reports_its_path(tmp_path: Path):
    config_path = tmp_path / LLM_CONFIGURATION_FILENAME
    config_path.write_text("unknown_option: true\n", encoding="utf8")

    with pytest.raises(ValueError, match=re.escape(str(config_path))):
        _make_driver(tmp_path).read_configuration_file()


def test_configuration_values_are_passed_to_agent_spec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        driver_module,
        "IdeaTool",
        SimpleNamespace(from_any=lambda **_: SimpleNamespace(tools=[])),
    )
    monkeypatch.setattr(
        driver_module,
        "WorkspaceExplorer",
        SimpleNamespace(from_any=lambda **_: SimpleNamespace(tools="explorer-tool")),
    )
    monkeypatch.setattr(driver_module, "InvocationHooks", SimpleNamespace(from_any=lambda **_: None))
    monkeypatch.setattr(
        driver_module,
        "AgentInvocationSpec",
        SimpleNamespace(from_any=lambda **kwargs: captured.update(kwargs) or "agent-spec"),
    )
    monkeypatch.setattr(driver_module, "TaskSpec", SimpleNamespace(from_specs=lambda specs: specs))
    configuration = LLMConfiguration(
        llm_param=LLMParam(temperature=0.4),
        usage_limit=UsageLimit(max_requests=5),
        connection_name="local",
    )

    monkeypatch.setattr(driver_module, "_construct_system_prompt", lambda **_: "system")
    buffer_message = LLMMessage.from_prompt(user="buffer history")
    llm_buffer_codec = LLMBufferCodec(messages_domain=LLMMessagesCodec().encode([buffer_message]))
    result = _make_task_spec(
        cast(IdeaSpace, SimpleNamespace(root_folder_path=tmp_path)),
        llm_buffer_codec,
        llm_configuration=configuration,
    )

    context_message = LLMMessage.from_prompt(user="context history")
    new_message = LLMMessage.from_prompt(user="current")
    context = ExecutionContext(llm_param=None, connection=None, llm_messages=[context_message])
    create_request = cast(Callable[[LLMMessageLike | None, ExecutionContext], LLMRequest], captured["create_request"])
    request = create_request(new_message, context)
    request_without_new_message = create_request(None, context)

    assert result == ["agent-spec"]
    assert request.messages == [buffer_message, new_message]
    assert request_without_new_message.messages == [buffer_message]
    assert request.system_prompt is not None
    assert captured["llm_param"] == configuration.llm_param
    assert captured["usage_limit"] == configuration.usage_limit
    assert captured["connection"] == "local"
