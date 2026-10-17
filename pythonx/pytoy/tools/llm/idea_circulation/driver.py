import logging
from dataclasses import replace
from pathlib import Path
from typing import Callable, ClassVar, Self

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMMessage, LLMRequest
from pytoy_llm.models.parts import TextPart

from pytoy.shared.lib.outcome import is_error
from pytoy.shared.pytoy_configuration import PytoyConfiguration
from pytoy.shared.ui import PytoyBuffer
from pytoy.tool_execution.llm import LLMExecutionExit, LLMExecutionHandler
from pytoy.tool_session.llm import (
    LLMMessageLike,
    LLMSessionBufferProvider,
    LLMSessionDriverProtocol,
    TaskRequest,
)

from .buffer_codec import LLMBufferCodec
from .messages_codec import LLMMessagesCodec
from .metadata_codec import BufferMetadataCodec
from .orchestrator.task_creators import IdeaExchangeResponse, create_idea_exchange_task_spec
from .statuses import IdeaCirculationStatus


class IdeaCirculationDriver(LLMSessionDriverProtocol):
    kind: ClassVar[str] = "idea-circulation"

    def __init__(
        self,
        idea_space: IdeaSpace,
        workspace: Path | None,
        status: IdeaCirculationStatus,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._idea_space = idea_space
        self._workspace = workspace
        self._status = status
        self._status.value_cycle_working_status = "idle"
        self._logger = logger or PytoyConfiguration().get_logger(location="global", level=logging.INFO)

    @classmethod
    def from_any(
        cls,
        idea_space_folder: str | Path | IdeaSpace,
        status: IdeaCirculationStatus,
        workspace: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> Self:
        if not isinstance(idea_space_folder, IdeaSpace):
            idea_space = IdeaSpace.from_path(path=idea_space_folder, with_creation=True)
        else:
            idea_space = idea_space_folder
        return cls(idea_space=idea_space, workspace=workspace, status=status, logger=logger)

    def make_progress(
        self,
        execution_creator: Callable[[TaskRequest], LLMExecutionHandler],
        llm_buffer_provider: LLMSessionBufferProvider,
        llm_message: LLMMessageLike | None,
    ) -> None:

        buffer = llm_buffer_provider.provide()
        llm_buffer_codec = LLMBufferCodec.from_llm_buffer(buffer.content)
        message_history = LLMMessagesCodec().decode(llm_buffer_codec.messages_domain)

        task_spec = create_idea_exchange_task_spec(message_history, self._idea_space, workspace=self._workspace)
        task_request = TaskRequest(spec=task_spec, input=llm_message)

        execution_handler = execution_creator(task_request)
        execution_handler.on_exit.subscribe(
            lambda exit_entity: self.on_exit(exit_entity, llm_buffer_provider=llm_buffer_provider)
        )
        self._status.value_cycle_working_status = "working"
        self.on_start(llm_message, buffer)
        execution_handler.start()
        self.update_buffer_metadata(buffer)

    def on_start(
        self,
        llm_message: LLMMessageLike | None,
        buffer: PytoyBuffer,
    ):
        if llm_message is None:
            return
        buffer_codec = LLMBufferCodec.from_llm_buffer(buffer.content)
        new_messages = LLMRequest.from_any(llm_message).messages
        new_message_text = LLMMessagesCodec().encode(new_messages)
        buffer_codec = replace(
            buffer_codec,
            messages_domain=buffer_codec.messages_domain + f"\n\n{new_message_text}\n\n",
        )
        replace_patch = buffer_codec.create_patch(buffer.content)
        buffer.range_operator.apply_patch(replace_patch)

    def on_exit(self, exit_entity: LLMExecutionExit, llm_buffer_provider: LLMSessionBufferProvider) -> None:
        buffer = llm_buffer_provider.provide()
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            buffer.append(str(exception))
        else:
            result = exit_entity.outcome.value
            self._status.update_tokens(result.task_result.llm_tokens)

            response = result.output
            if isinstance(response, IdeaExchangeResponse):
                if response.status_patch:
                    response.status_patch.apply(self._status)
                new_message = LLMMessage.from_parts(parts=[TextPart(role="assistant", content=response.message)])
                llm_messages = [*result.context_state.llm_messages, new_message]
            elif isinstance(response, str):
                llm_messages = result.context_state.llm_messages
            else:
                new_message = LLMMessage.from_parts(parts=[TextPart(role="assistant", content=str(response))])
                llm_messages = [*result.context_state.llm_messages, new_message]

            messages_text = LLMMessagesCodec().encode(llm_messages)
            replace_patch = LLMBufferCodec(messages_domain=messages_text).create_patch(buffer.content)
            buffer.range_operator.apply_patch(replace_patch)

        self._status.value_cycle_working_status = "idle"
        self.update_buffer_metadata(buffer)

    def update_buffer_metadata(self, buffer: PytoyBuffer) -> None:
        metadata_codec = BufferMetadataCodec.from_any(status=self._status)
        patch = metadata_codec.create_patch(buffer.content)
        buffer.range_operator.apply_patch(patch)

    @property
    def status(self) -> IdeaCirculationStatus:
        return self._status

    @property
    def idea_space(self) -> IdeaSpace:
        return self._idea_space

    @property
    def folder_path(self) -> Path:
        return self.idea_space.folder_path
