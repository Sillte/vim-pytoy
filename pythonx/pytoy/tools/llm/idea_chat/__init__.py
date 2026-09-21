from dataclasses import replace
from pathlib import Path
from typing import Callable, Self

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.ideas.stories.three_word_story import ThreeWordStoryStudio
from pytoy_llm.models import LLMMessage, LLMMessagesLike
from pytoy_llm.task.models import AgentInvocationSpec, ExecutionContext, TaskContextState, TaskSpec
from pytoy_llm.tools.idea_tool.idea_tool import IdeaTool

from pytoy.devtools.debug_logger import DebugLogger
from pytoy.shared.lib.events.domain.action import Keys
from pytoy.shared.lib.outcome import is_error
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import BufferSource, make_buffer
from pytoy.tool_execution.llm import (
    LLMExecutionExit,
    LLMExecutionHandler,
    LLMExecutionHooks,
    LLMExecutionRequest,
    LLMExecutionResult,
)
from pytoy.tool_session.llm import (
    LLMSessionBufferHooks,
    LLMSessionBufferProvider,
    LLMSessionDriverProtocol,
    LLMSessionHandler,
    LLMSessionQuery,
    LLMSessionRequest,
    TaskExecutionExit,
    TaskRequest,
    TaskSessionHandler,
)

from .buffer_codec import LLMBufferCodec
from .messages_codec import LLMMessagesCodec


def _make_task_spec(
    idea_space: IdeaSpace, llm_buffer_codec: LLMBufferCodec, user_prompt: str, workspace: Path | None = None
) -> TaskSpec:
    if llm_buffer_codec.messages_domain is None:
        raise ValueError("Invalid LLMBufferCodec")
    llm_messages = LLMMessagesCodec().decode(llm_buffer_codec.messages_domain)

    def _create_messages(input: str, context: ExecutionContext) -> LLMMessagesLike:
        # If other `context` would be preferrable, `ExecutionContext` is utlized.
        new_llm_message = LLMMessage.from_prompt(user=user_prompt)
        messages = [*llm_messages, new_llm_message]
        logger = DebugLogger()
        logger.log(messages)
        logger.log(messages[-1])
        return messages

    if workspace is None:
        workspace = idea_space.root
    idea_tool = IdeaTool.from_any(idea_space_root=idea_space.root, workspace_root=workspace)
    tools = [idea_tool]

    return TaskSpec.from_specs(
        [AgentInvocationSpec.from_any(create_messages=_create_messages, output_type=str, tools=tools)],
    )


class IdeaChatDriver(LLMSessionDriverProtocol):
    def __init__(self, idea_space: IdeaSpace) -> None:
        self._idea_space = idea_space

    @classmethod
    def from_any(cls, idea_space_folder: str | Path | IdeaSpace) -> Self:
        if not isinstance(idea_space_folder, IdeaSpace):
            idea_space = IdeaSpace.from_path(path=idea_space_folder)
        else:
            idea_space = idea_space_folder
        return cls(idea_space=idea_space)

    def make_progress(
        self,
        execution_creator: Callable[[TaskRequest], LLMExecutionHandler],
        llm_buffer_provider: LLMSessionBufferProvider,
        user_prompt: str,
    ) -> None:
        buffer = llm_buffer_provider.provide()
        content = buffer.content
        idea_chat = LLMBufferCodec.from_llm_buffer(content)

        codec = idea_chat.from_llm_buffer(content)
        if not codec.valid:
            buffer.append(LLMBufferCodec.provide_empty_domain())
            content = buffer.content
            codec = LLMBufferCodec.from_llm_buffer(content)
        if not codec.valid:
            raise ValueError("Inconsistency of `Buffer` in views of `LLMBufferCodec`. ")

        task_spec = _make_task_spec(self._idea_space, codec, user_prompt)
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
        buffer.show()
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            buffer.append(str(exception))
        else:
            result = exit_entity.outcome.value
            messages_text = LLMMessagesCodec().encode(result.context_state.llm_messages)

            logger = DebugLogger()
            logger.log(result.context_state.llm_messages)
            replace_patch = LLMBufferCodec(messages_domain=messages_text).create_patch(buffer.content)
            if replace_patch is not None:
                buffer.range_operator.replace_lines(replace_patch.line_range, replace_patch.lines)
            else:
                print("FAILED to Insert the history... `on_exit` of `IdeaChatDriver`. ")

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


class IdeaChatHandler:
    kind = "idea-chat"
    buffer_name = "__idea-chat__"

    def __init__(self, session_handler: LLMSessionHandler) -> None:
        self._session_handler = session_handler

    @classmethod
    def from_any(cls, idea_space: IdeaSpace | Path | str) -> Self:
        query = LLMSessionQuery.from_any(kind=cls.kind)
        llm_handlers = LLMSessionHandler.query(query)
        if llm_handlers:
            return cls(llm_handlers[0])
        if not isinstance(idea_space, IdeaSpace):
            idea_space = IdeaSpace.from_path(idea_space)
        buffer_name = IdeaChatHandler.buffer_name
        request = LLMSessionRequest.from_any(
            driver=IdeaChatDriver.from_any(idea_space),
            buffer_source=BufferSource.from_no_file(name=buffer_name),
            buffer_hooks=IdeaChatDriver.build_buffer_hooks(idea_space),
            kind=cls.kind,
        )
        llm_handler = LLMSessionHandler.create(request)
        return cls(llm_handler)

    def make_progress(self, user_prompt: str):
        self._session_handler.make_progress(user_prompt)

    def provide_buffer(
        self,
    ) -> PytoyBuffer:
        return self.provide_buffer()
