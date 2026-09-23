from pathlib import Path
from typing import Self

from pytoy_llm.idea import IdeaSpace

from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery, LLMSessionRequest
from pytoy.tools.llm.idea_chat.driver import IdeaChatDriver


class IdeaChatHandler:
    kind = IdeaChatDriver.kind
    buffer_name = "__idea-chat__"

    def __init__(self, session_handler: LLMSessionHandler) -> None:
        self._session_handler = session_handler

    @property
    def session_handler(self) -> LLMSessionHandler:
        return self._session_handler

    @classmethod
    def from_any(cls, idea_space: IdeaSpace | Path | str, workspace: Path | None = None) -> Self:
        if not isinstance(idea_space, IdeaSpace):
            Path(idea_space).mkdir(exist_ok=True, parents=True)
            idea_space = IdeaSpace.from_path(idea_space)
        idea_space.ensure_root_marker()
        idea_space_path = idea_space.root.resolve()
        workspace_path = (workspace or idea_space.root).resolve()
        metadata = {"idea-space": idea_space_path, "workspace": workspace_path}
        query = LLMSessionQuery.from_any(kind=cls.kind, metadata=metadata)
        llm_handlers = LLMSessionHandler.query(query)
        if llm_handlers:
            return cls(llm_handlers[0])
        existing_handlers = LLMSessionHandler.query(LLMSessionQuery.from_any(kind=cls.kind))
        if existing_handlers:
            raise ValueError(
                "An idea-chat session already exists for different metadata: "
                f"{existing_handlers[0].metadata} != {metadata}"
            )
        buffer_name = IdeaChatHandler.buffer_name
        request = LLMSessionRequest.from_any(
            driver=IdeaChatDriver.from_any(idea_space, workspace=workspace),
            buffer_source=BufferSource.from_no_file(name=buffer_name),
            buffer_hooks=IdeaChatDriver.build_buffer_hooks(idea_space),
            kind=cls.kind,
            metadata=metadata,
        )
        llm_handler = LLMSessionHandler.create(request)
        return cls(llm_handler)

    def make_progress(self, user_prompt: str):
        self._session_handler.make_progress(user_prompt)

    def provide_buffer(
        self,
    ) -> PytoyBuffer:
        return self._session_handler.buffer_provider.provide()

    def terminate(self) -> None:
        self._session_handler.terminate()
