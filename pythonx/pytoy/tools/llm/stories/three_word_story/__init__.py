from pathlib import Path
from typing import Callable, Self

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.ideas.stories.three_word_story import ThreeWordStoryStudio

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


class ThreeWordStoryDriver(LLMSessionDriverProtocol):
    def __init__(self, studio: ThreeWordStoryStudio) -> None:
        self._studio = studio

    def make_progress(
        self,
        execution_creator: Callable[[TaskRequest], LLMExecutionHandler],
        llm_buffer_provider: LLMSessionBufferProvider,
        user_prompt: str,
    ) -> None:
        task_spec = self._studio.make_task_spec(usage_limit=None)
        task_request = TaskRequest(spec=task_spec, input=user_prompt)
        self.on_start(user_prompt, llm_buffer_provider)
        execution_handler = execution_creator(task_request)
        execution_handler.on_exit.subscribe(lambda exit_entity: self.on_exit(exit_entity, llm_buffer_provider))
        execution_handler.start()

    def on_start(self, user_prompt: str, llm_buffer_provider: LLMSessionBufferProvider):
        buffer = llm_buffer_provider.provide()
        lines = user_prompt.splitlines()
        length = max((len(elem) for elem in lines), default=5)
        lines = ["-" * length, *lines, "-" * length]
        buffer.append("\n".join(lines))

    def on_exit(self, exit_entity: LLMExecutionExit, llm_buffer_provider: LLMSessionBufferProvider) -> None:
        buffer = llm_buffer_provider.provide()
        if window := buffer.window:
            window.focus()
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            buffer.append(str(exception))
        else:
            output = exit_entity.outcome.value.output
            buffer.append(output)

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


class ThreeWordStoryHandler:
    kind = "ThreeWordStory"
    buffer_name = "__three-word-story__"

    def __init__(self, idea_space_llm_handler: LLMSessionHandler) -> None:
        self.idea_space_llm_handler = idea_space_llm_handler

    @classmethod
    def from_any(cls, space_path: Path | str) -> Self:
        query = LLMSessionQuery.from_any(kind=cls.kind)
        llm_handlers = LLMSessionHandler.query(query)
        if llm_handlers:
            return cls(llm_handlers[0])
        Path(space_path).mkdir(exist_ok=True, parents=True)
        idea_space = IdeaSpace.from_path(space_path)

        request = LLMSessionRequest.from_any(
            driver=ThreeWordStoryDriver(ThreeWordStoryStudio.from_any(idea_space.folder_path)),
            buffer_source=BufferSource.from_no_file(name=cls.buffer_name),
            buffer_hooks=ThreeWordStoryDriver.build_buffer_hooks(idea_space),
            kind=cls.kind,
        )
        llm_handler = LLMSessionHandler.create(request)
        return cls(llm_handler)

    def make_progress(self, user_prompt: str):
        self.idea_space_llm_handler.make_progress(user_prompt)
