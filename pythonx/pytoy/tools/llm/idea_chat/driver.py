import shutil
from dataclasses import replace
from pathlib import Path
from typing import Callable, Self

from pytoy_llm.activity_sinks import LoggerActivitySink
from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMMessage, LLMMessagesLike
from pytoy_llm.task.models import AgentInvocationSpec, ExecutionContext, InvocationHooks, TaskSpec
from pytoy_llm.tools.idea_tool import IdeaTool

from pytoy.devtools.debug_logger import DebugLogger
from pytoy.shared.lib.events.domain.action import Keys
from pytoy.shared.lib.outcome import is_error
from pytoy.shared.pytoy_configuration import PytoyConfiguration
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.tool_execution.llm import LLMExecutionExit, LLMExecutionHandler
from pytoy.tool_session.llm import (
    LLMSessionBufferHooks,
    LLMSessionBufferProvider,
    LLMSessionDriverProtocol,
    TaskRequest,
)
from pytoy.tools.llm.idea_chat.buffer_codec import LLMBufferCodec
from pytoy.tools.llm.idea_chat.messages_codec import LLMMessagesCodec
from pytoy.tools.llm.idea_chat.prompts import CONVENTION, SYSTEM_PROMPT


def _make_task_spec(
    idea_space: IdeaSpace, llm_buffer_codec: LLMBufferCodec, user_prompt: str, workspace: Path | None = None
) -> TaskSpec:
    if llm_buffer_codec.messages_domain is None:
        raise ValueError("Invalid LLMBufferCodec")
    llm_messages = LLMMessagesCodec().decode(llm_buffer_codec.messages_domain)

    def _create_messages(input: str, context: ExecutionContext) -> LLMMessagesLike:
        # If other `context` would be preferrable, `ExecutionContext` is utilized.
        new_llm_message = LLMMessage.from_prompt(user=user_prompt, system=SYSTEM_PROMPT)
        messages = [*llm_messages, new_llm_message]
        return messages

    if workspace is None:
        workspace = idea_space.root
    idea_tool = IdeaTool.from_any(idea_space_root=idea_space.root, workspace_root=workspace)
    hooks = InvocationHooks.from_any(
        on_start=lambda _: idea_tool.mark_llm_start(), on_completion=lambda _: idea_tool.mark_llm_finished()
    )
    tools = [idea_tool]
    spec = AgentInvocationSpec.from_any(create_messages=_create_messages, output_type=str, tools=tools, hooks=hooks)

    return TaskSpec.from_specs(
        [spec],
    )


class IdeaChatDriver(LLMSessionDriverProtocol):
    def __init__(self, idea_space: IdeaSpace, workspace: Path | None) -> None:
        self._idea_space = idea_space
        self._workspace = workspace

    @classmethod
    def from_any(cls, idea_space_folder: str | Path | IdeaSpace, workspace: Path | None = None) -> Self:
        if not isinstance(idea_space_folder, IdeaSpace):
            idea_space = IdeaSpace.from_path(path=idea_space_folder)
        else:
            idea_space = idea_space_folder
        return cls(idea_space=idea_space, workspace=workspace)

    def make_progress(
        self,
        execution_creator: Callable[[TaskRequest], LLMExecutionHandler],
        llm_buffer_provider: LLMSessionBufferProvider,
        user_prompt: str,
    ) -> None:

        buffer = llm_buffer_provider.provide()
        DebugLogger().log(f"buffer:{buffer.content}")
        codec = LLMBufferCodec.from_llm_buffer(buffer.content)
        DebugLogger().log(f"codec:{codec}")
        if not codec.valid:
            buffer.append(LLMBufferCodec.provide_empty_domain())
            DebugLogger().log(f"buffer:{buffer.content}")
            codec = LLMBufferCodec.from_llm_buffer(buffer.content)
            DebugLogger().log(f"codec:{codec}")
        if not codec.valid:
            raise ValueError("Inconsistency of `Buffer` in views of `LLMBufferCodec`. ")
        self._prepare_idea_space()

        task_spec = _make_task_spec(self._idea_space, codec, user_prompt, workspace=self._workspace)

        logger = PytoyConfiguration().get_logger(location="global", level=10)
        activity_sink = LoggerActivitySink(logger=logger)
        task_request = TaskRequest(spec=task_spec, input=user_prompt, activity_sink=activity_sink)

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
        if buffer_codec.messages_domain is None:
            raise ValueError("Implemetation Error.")
        message_codec = LLMMessagesCodec()
        new_message = message_codec.make_part_from_user_prompt(user_prompt)
        buffer_codec = replace(buffer_codec, messages_domain=buffer_codec.messages_domain + f"\n\n{new_message}\n\n")

        replace_patch = buffer_codec.create_patch(buffer.content)
        if replace_patch is None:
            raise RuntimeError("`ReplacePatch` cannot be created.")
        buffer.range_operator.replace_lines(replace_patch.line_range, replace_patch.lines)

    def on_exit(self, exit_entity: LLMExecutionExit, llm_buffer_provider: LLMSessionBufferProvider) -> None:
        buffer = llm_buffer_provider.provide()
        if window := buffer.window:
            window.focus()
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            buffer.append(str(exception))
        else:
            result = exit_entity.outcome.value
            messages_text = LLMMessagesCodec().encode(result.context_state.llm_messages)
            replace_patch = LLMBufferCodec(messages_domain=messages_text).create_patch(buffer.content)
            if replace_patch is not None:
                buffer.range_operator.replace_lines(replace_patch.line_range, replace_patch.lines)
            else:
                pass

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

    def _prepare_idea_space(self) -> None:
        convention_path = self.folder_path / ".convention.md"
        if not self.folder_path.exists():
            self.folder_path.mkdir(exist_ok=True, parents=True)
            convention_path.write_text(CONVENTION)
        sub_names = ["surveys", "issues"]
        for sub_name in sub_names:
            (self.folder_path / sub_name).mkdir(exist_ok=True)

    def clear_idea_space(self) -> None:
        for child in self.folder_path.iterdir():
            if child.name == ".convention.md":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
