from typing import Self, Sequence

from pytoy_llm.task.models import TaskRequest

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.tool_execution.llm import LLMExecutionHandler

from .manager import IdeaSpaceLLMManager
from .models import (
    LLMSession,
    LLMSessionBufferProvider,
    LLMSessionID,
    LLMSessionQuery,
    LLMSessionRequest,
)


class LLMSessionHandler:
    def __init__(self, id: LLMSessionID, *, manager: IdeaSpaceLLMManager):
        self._id = id
        self._manager = manager

    @classmethod
    def create(cls, request: LLMSessionRequest, *, manager: IdeaSpaceLLMManager | None = None) -> Self:
        manager = manager or GlobalPytoyContext.get().idea_space_llm_session_manager
        session = LLMSession.from_request(request)
        manager.register(session)
        return cls(id=session.id, manager=manager)

    @classmethod
    def query(cls, query: LLMSessionQuery, *, manager: IdeaSpaceLLMManager | None = None) -> Sequence[Self]:
        manager = manager or GlobalPytoyContext.get().idea_space_llm_session_manager
        sessions = manager.select(query)
        return [cls(id=session.id, manager=manager) for session in sessions]

    @property
    def buffer_provider(self) -> LLMSessionBufferProvider:
        return self._require_session().buffer_provider

    def make_progress(self, user_prompt: str) -> None:
        session = self._require_session()
        session.driver.make_progress(
            execution_creator=self.make_execution_handler,
            llm_buffer_provider=session.buffer_provider,
            user_prompt=user_prompt,
        )

    def make_execution_handler(self, task_request: TaskRequest) -> LLMExecutionHandler:
        session = self._require_session()
        task_execution_handler = session.task_session_handler.create_task(task_request)
        return LLMExecutionHandler.create_from_task_handler(task_execution_handler, kind=session.kind)

    def _require_session(self) -> LLMSession:
        session = self._manager.get(self._id)
        if session is None:
            raise ValueError(f"Session is already eliminated. `{self._id=}`")
        return session
