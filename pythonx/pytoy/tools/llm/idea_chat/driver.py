from dataclasses import replace
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Callable, ClassVar, Literal, Self, assert_never

import yamlrocks
from pydantic import BaseModel, ConfigDict, Field
from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMMessage, LLMParam, LLMRequest, LLMRequestLike, LLMTokens, UsageLimit
from pytoy_llm.task.audit import TaskAuditor
from pytoy_llm.task.models import AgentInvocationSpec, ExecutionContext, InvocationHooks, TaskResult, TaskSpec
from pytoy_llm.tools.idea_tool import IdeaTool
from pytoy_llm.tools.workspace_explorer import WorkspaceExplorer

from pytoy.shared.lib.events.domain.action import Keys
from pytoy.shared.lib.outcome import is_error
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.shared.ui.pytoy_window import PytoyWindow
from pytoy.tool_execution.llm import LLMExecutionExit, LLMExecutionHandler
from pytoy.tool_session.llm import (
    LLMSessionBufferHooks,
    LLMSessionBufferProvider,
    LLMSessionDriverProtocol,
    TaskRequest,
)
from pytoy.tools.llm.idea_chat.buffer_codec import LLMBufferCodec
from pytoy.tools.llm.idea_chat.messages_codec import LLMMessagesCodec
from pytoy.tools.llm.idea_chat.metadata_codec import BufferMetadataCodec
from pytoy.tools.llm.idea_chat.prompts import BASE_SYSTEM_PROMPT, CONVENTION, DASHBOARD_TEMPLATE, SYSTEM_PERSONALITY

BASE_SYSTEM_PROMPT_FILENAME = "base_system_prompt.md"
SYSTEM_PERSONALITY_FILENAME = "system_personality.md"
LLM_CONFIGURATION_FILENAME = "llm_configuration.yaml"
AUDIT_FOLDERNAME = "audit"
LLM_CONFIGURATION_TEMPLATE = dedent(
    """\
    # Configuration for Idea-Chat LLM.
    # when `null` or unspecified, the default value is used.

    # llm_param:
    #   reasoning_effort: medium
    #   verbosity: high
    #   max_tokens: 4096
    llm_param: null

    # The limitation of usage.
    # usage_limit:
    #   max_total_tokens: 50000
    #   max_requests: 20
    usage_limit: null

    # The name of connection, refer to `:LLM config` and `default`
    connection_name: null
    """
)

type MetadataDetailLevel = Literal["summary", "detail"]


class LLMConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_param: LLMParam | None = None
    usage_limit: UsageLimit | None = None
    connection_name: str | None = Field(default=None, min_length=1)


def _construct_system_prompt(idea_space: IdeaSpace) -> str:
    base_system_prompt_path = idea_space.root_space.space_meta_folder / BASE_SYSTEM_PROMPT_FILENAME
    system_personality_path = idea_space.root_space.space_meta_folder / SYSTEM_PERSONALITY_FILENAME
    if base_system_prompt_path.exists():
        base_system_prompt = base_system_prompt_path.read_text(encoding="utf8")
    else:
        base_system_prompt_path.write_text(BASE_SYSTEM_PROMPT, encoding="utf8")
        base_system_prompt = BASE_SYSTEM_PROMPT

    if system_personality_path.exists():
        system_personality = system_personality_path.read_text(encoding="utf8")
    else:
        system_personality_path.write_text(SYSTEM_PERSONALITY, encoding="utf8")
        system_personality = SYSTEM_PERSONALITY

    return "\n\n".join([elem.strip() for elem in [base_system_prompt, system_personality]])


def _dump_task_audit(idea_space: IdeaSpace, task_result: TaskResult) -> None:
    audit_folder = idea_space.root_space.space_meta_folder / AUDIT_FOLDERNAME
    audit_folder.mkdir(exist_ok=True, parents=True)
    file_path = audit_folder / f"{datetime.now():%Y%m%d_%H%M%S}.json"
    try:
        TaskAuditor.from_task_result(task_result).dump(file_path)
    except OSError:
        pass


def _make_task_spec(
    idea_space: IdeaSpace,
    llm_buffer_codec: LLMBufferCodec,
    user_prompt: str,
    llm_configuration: LLMConfiguration,
    workspace: Path | None = None,
) -> TaskSpec:
    llm_messages = LLMMessagesCodec().decode(llm_buffer_codec.messages_domain)

    def _create_request(input: str, context: ExecutionContext) -> LLMRequestLike:
        # If other `context` would be preferrable, `ExecutionContext` is utilized.
        system_prompt = _construct_system_prompt(idea_space=idea_space)
        new_llm_message = LLMMessage.from_prompt(user=user_prompt)
        messages = [*llm_messages, new_llm_message]
        return LLMRequest.from_any(messages, system_prompt=system_prompt)

    if workspace is None:
        workspace = idea_space.root_folder_path
    idea_tool = IdeaTool.from_any(idea_space_roots=idea_space.root_folder_path, workspace_root=workspace)
    workspace_explorer = WorkspaceExplorer.from_any(workspace=workspace, ignored_roots=[idea_space.root_folder_path])
    hooks = InvocationHooks.from_any(
        on_start=lambda _: idea_tool.mark_llm_start(), on_completion=lambda _: idea_tool.mark_llm_finished()
    )
    tools = [*idea_tool.tools, workspace_explorer.tools]
    spec = AgentInvocationSpec.from_any(
        create_request=_create_request,
        output_type=str,
        tools=tools,
        connection=llm_configuration.connection_name,
        llm_param=llm_configuration.llm_param,
        usage_limit=llm_configuration.usage_limit,
        hooks=hooks,
    )

    return TaskSpec.from_specs(
        [spec],
    )


class IdeaChatDriver(LLMSessionDriverProtocol):
    kind: ClassVar[str] = "idea-chat"

    def __init__(self, idea_space: IdeaSpace, workspace: Path | None) -> None:
        self._idea_space = idea_space
        self._workspace = workspace
        self._llm_tokens = LLMTokens(prompt=0, completion=0, total=0, cache_read=0, cache_write=0)
        self._llm_configuration = LLMConfiguration()
        self._metadata_detail_level: MetadataDetailLevel = "summary"

    @classmethod
    def from_any(cls, idea_space_folder: str | Path | IdeaSpace, workspace: Path | None = None) -> Self:
        if not isinstance(idea_space_folder, IdeaSpace):
            idea_space = IdeaSpace.from_path(path=idea_space_folder)
        else:
            idea_space = idea_space_folder
        return cls(idea_space=idea_space, workspace=workspace)

    def initialized_session(self, llm_buffer_provider: LLMSessionBufferProvider) -> None:
        buffer = llm_buffer_provider.provide()
        self._prepare_idea_space()
        self._llm_configuration = self.read_configuration_file()
        self._update_buffer_metadata(buffer)

    def make_progress(
        self,
        execution_creator: Callable[[TaskRequest], LLMExecutionHandler],
        llm_buffer_provider: LLMSessionBufferProvider,
        user_prompt: str,
    ) -> None:

        buffer = llm_buffer_provider.provide()
        self._llm_configuration = self.read_configuration_file()
        self._update_buffer_metadata(buffer)

        codec = LLMBufferCodec.from_llm_buffer(buffer.content)
        patch = codec.create_patch(buffer.content)
        buffer.range_operator.apply_patch(patch)

        task_spec = _make_task_spec(
            self._idea_space,
            codec,
            user_prompt,
            llm_configuration=self._llm_configuration,
            workspace=self._workspace,
        )
        task_request = TaskRequest(spec=task_spec, input=user_prompt)

        self.on_start(user_prompt, buffer, codec)
        execution_handler = execution_creator(task_request)
        execution_handler.on_exit.subscribe(lambda exit_entity: self.on_exit(exit_entity, llm_buffer_provider))
        execution_handler.start()

    def on_start(
        self,
        user_prompt: str,
        buffer: PytoyBuffer,
        buffer_codec: LLMBufferCodec,
    ):

        message_codec = LLMMessagesCodec()
        new_message = message_codec.make_part_from_user_prompt(user_prompt)
        buffer_codec = replace(buffer_codec, messages_domain=buffer_codec.messages_domain + f"\n\n{new_message}\n\n")

        replace_patch = buffer_codec.create_patch(buffer.content)
        buffer.range_operator.apply_patch(replace_patch)

    def on_exit(self, exit_entity: LLMExecutionExit, llm_buffer_provider: LLMSessionBufferProvider) -> None:
        buffer = llm_buffer_provider.provide()
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            buffer.append(str(exception))
        else:
            result = exit_entity.outcome.value
            self._llm_tokens = LLMTokens.aggregate((self._llm_tokens, result.task_result.llm_tokens))
            messages_text = LLMMessagesCodec().encode(result.context_state.llm_messages)
            replace_patch = LLMBufferCodec(messages_domain=messages_text).create_patch(buffer.content)
            buffer.range_operator.apply_patch(replace_patch)
            self._update_buffer_metadata(buffer)

            _dump_task_audit(self._idea_space, result.task_result)

    @classmethod
    def build_buffer_hooks(cls, idea_space: IdeaSpace) -> LLMSessionBufferHooks:
        # TODO: We have to condier the special handling of the links based on the `idea_space`
        actions = dict()

        def on_creation(buffer):
            buffer.metadata.data["idea-space"] = idea_space

        def _open_file():
            convention = idea_space.convention
            if convention:
                make_buffer(source=convention.file_path)

        actions[Keys.ENTER] = lambda buffer: _open_file()
        actions["<leader>m"] = lambda buffer: _open_file()

        return LLMSessionBufferHooks(actions=actions, on_creation=on_creation)

    @property
    def idea_space(self) -> IdeaSpace:
        return self._idea_space

    @property
    def folder_path(self) -> Path:
        return self.idea_space.folder_path

    def open_configuration_file(self) -> None:
        configuration_file_path = self._idea_space.root_space.space_meta_folder / LLM_CONFIGURATION_FILENAME
        configuration_file_path.parent.mkdir(exist_ok=True, parents=True)
        if not configuration_file_path.exists():
            configuration_file_path.write_text(LLM_CONFIGURATION_TEMPLATE, encoding="utf8")
        PytoyWindow.open(configuration_file_path, param="vertical")

    def read_configuration_file(self) -> LLMConfiguration:
        configuration_file_path = self._idea_space.root_space.space_meta_folder / LLM_CONFIGURATION_FILENAME
        if not configuration_file_path.exists():
            return LLMConfiguration()

        try:
            raw_configuration = yamlrocks.loads(configuration_file_path.read_text(encoding="utf8"))
            return LLMConfiguration.model_validate({} if raw_configuration is None else raw_configuration)
        except Exception as exc:
            raise ValueError(f"Invalid IdeaChat LLM configuration in {configuration_file_path}: {exc}") from exc

    def set_metadata_detail_level(self, level: MetadataDetailLevel, buffer_provider: LLMSessionBufferProvider) -> None:
        if self._metadata_detail_level == level:
            return
        self._metadata_detail_level = level
        buffer = buffer_provider.provide()
        self._update_buffer_metadata(buffer)

    def _update_buffer_metadata(self, buffer: PytoyBuffer):
        dashboard_path = self.folder_path / "dashboard.md"
        workspace_name = self._workspace.name if self._workspace else None
        metadata = BufferMetadataCodec.from_dashboard(
            dashboard_path,
            kind=self.kind,
            workspace_name=workspace_name,
        )

        match self._metadata_detail_level:
            case "detail":
                metadata = replace(
                    metadata,
                    llm_tokens=self._llm_tokens,
                    llm_param=self._llm_configuration.llm_param,
                    usage_limit=self._llm_configuration.usage_limit,
                    connection_name=self._llm_configuration.connection_name,
                )
            case "summary":
                pass
            case _:
                assert_never(self._metadata_detail_level)

        patch = metadata.create_patch(buffer.content)
        buffer.range_operator.apply_patch(patch)

    def _prepare_idea_space(self) -> None:
        convention_path = self.folder_path / ".convention.md"
        dashboard_path = self.folder_path / "dashboard.md"
        if not self.folder_path.exists():
            self.folder_path.mkdir(exist_ok=True, parents=True)
        if not convention_path.exists():
            convention_path.write_text(CONVENTION, encoding="utf8")
        sub_names = ["llm_notes", "outputs"]
        for sub_name in sub_names:
            (self.folder_path / sub_name).mkdir(exist_ok=True)
        if not dashboard_path.exists():
            dashboard_path.write_text(DASHBOARD_TEMPLATE, encoding="utf8")
