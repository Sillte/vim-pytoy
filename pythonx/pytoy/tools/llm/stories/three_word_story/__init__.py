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
        buffer.append("--" * 10)
        buffer.append(user_prompt)

    def on_exit(self, exit_entity: LLMExecutionExit, llm_buffer_provider: LLMSessionBufferProvider) -> None:
        buffer = llm_buffer_provider.provide()
        buffer.show()
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

        def _open_file():
            convention = idea_space.convention
            if convention:
                make_buffer(source=convention.file_path)

        actions[Keys.ENTER] = lambda buffer: _open_file()
        actions["<leader>m"] = lambda buffer: _open_file()
        actions["<F4>"] = lambda buffer: _open_file()

        return LLMSessionBufferHooks(actions=actions)


class ThreeWordsStoryController:
    kind = "ThreeWordsStory"

    def __init__(self, idea_space_llm_handler: LLMSessionHandler) -> None:
        self.idea_space_llm_handler = idea_space_llm_handler

    @classmethod
    def from_any(cls, space_path: Path | str) -> Self:
        query = LLMSessionQuery.from_any(kind=cls.kind)
        llm_handlers = LLMSessionHandler.query(query)
        if llm_handlers:
            return cls(llm_handlers[0])
        idea_space = IdeaSpace.from_path(space_path)
        buffer_name = "__idea_space__"
        request = LLMSessionRequest.from_any(
            driver=ThreeWordStoryDriver(ThreeWordStoryStudio.from_any(idea_space.folder_path)),
            buffer_source=BufferSource.from_no_file(name=buffer_name),
            buffer_hooks=ThreeWordStoryDriver.build_buffer_hooks(idea_space),
            kind=cls.kind,
        )
        llm_handler = LLMSessionHandler.create(request)
        return cls(llm_handler)

    def make_progress(self, user_prompt: str):
        self.idea_space_llm_handler.make_progress(user_prompt)


class ThreeWordsStoryControllerOld:
    kind = "ThreeWordStory"

    def __init__(self, studio: ThreeWordStoryStudio) -> None:
        self._studio = studio
        self._source = BufferSource.from_no_file("__llm_dialog__")

    @property
    def studio(self) -> ThreeWordStoryStudio:
        return self._studio

    @property
    def idea_space(self) -> IdeaSpace:
        return self._studio.idea_space

    @classmethod
    def from_any(cls, space_path: Path | str) -> Self:
        idea_space = IdeaSpace.from_path(space_path)
        studio = ThreeWordStoryStudio.from_any(idea_space.folder_path)
        return cls(studio=studio)

    def make_progress(self, user_prompt: str):
        task_spec = self.studio.make_task_spec(usage_limit=None)
        request = LLMExecutionRequest.from_any(task_spec=task_spec, input=user_prompt, kind=self.kind)
        llm_handler = LLMExecutionHandler.create(request)
        hooks = LLMExecutionHooks(on_result=self.on_result, on_exception=self.on_exception)
        self.on_start(user_prompt)
        llm_handler.start(hooks=hooks)

    def on_start(self, user_prompt: str):
        buffer = make_buffer(self._source)
        buffer.append("--" * 10)
        buffer.append(user_prompt)

    def on_result(self, result: LLMExecutionResult):
        buffer = make_buffer(self._source)
        buffer.append(result.output)
        buffer.show()

    def on_exception(self, exception: Exception):
        buffer = make_buffer(self._source)
        buffer.append(str(exception))
        buffer.show()
