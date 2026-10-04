from pathlib import Path
from typing import Self

from pytoy_llm.idea import IdeaSpace

from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery, LLMSessionRequest
from pytoy.tools.llm.idea_chat.driver import IdeaChatDriver, MetadataDetailLevel


class IdeaChatHandler:
    kind = IdeaChatDriver.kind
    buffer_name = "__idea-chat__"

    def __init__(self, session_handler: LLMSessionHandler, driver: IdeaChatDriver) -> None:
        self._session_handler = session_handler
        self._driver = driver

    @property
    def session_handler(self) -> LLMSessionHandler:
        return self._session_handler

    @classmethod
    def from_any(cls, idea_space: IdeaSpace | Path | str, workspace: Path | None = None) -> Self:
        if not isinstance(idea_space, IdeaSpace):
            Path(idea_space).mkdir(exist_ok=True, parents=True)
            idea_space = IdeaSpace.from_path(idea_space)
        idea_space.ensure_root_marker()
        idea_space_path = idea_space.folder_path
        workspace_path = (workspace or idea_space.root_folder_path).resolve()
        metadata = {"idea-space": idea_space_path, "workspace": workspace_path}
        query = LLMSessionQuery.from_any(kind=cls.kind, metadata=metadata)
        llm_handlers = LLMSessionHandler.query(query)
        if llm_handlers:
            llm_handler = llm_handlers[0]
            session_driver = llm_handler.driver
            if isinstance(session_driver, IdeaChatDriver):
                return cls(llm_handler, session_driver)
            else:
                raise RuntimeError("IdeaChatDriver is not preserved.")
        existing_handlers = LLMSessionHandler.query(LLMSessionQuery.from_any(kind=cls.kind))
        if existing_handlers:
            raise ValueError(
                "An idea-chat session already exists for different metadata: "
                f"{existing_handlers[0].metadata} != {metadata}"
            )
        buffer_name = IdeaChatHandler.buffer_name
        driver = IdeaChatDriver.from_any(idea_space, workspace=workspace)
        request = LLMSessionRequest.from_any(
            driver=driver,
            buffer_source=BufferSource.from_no_file(name=buffer_name),
            buffer_hooks=IdeaChatDriver.build_buffer_hooks(idea_space),
            kind=cls.kind,
            metadata=metadata,
        )
        llm_handler = LLMSessionHandler.create(request)
        try:
            driver.initialized_session(llm_handler.buffer_provider)
        except Exception:
            llm_handler.terminate()
            raise
        return cls(llm_handler, driver)

    def make_progress(self, user_prompt: str):
        self._session_handler.make_progress(user_prompt)

    def set_metadata_detail_level(self, metadata_detail_level: MetadataDetailLevel) -> None:
        self._driver.set_metadata_detail_level(metadata_detail_level, self._session_handler.buffer_provider)

    def open_configuration_file(self) -> None:
        self._driver.open_configuration_file()

    def provide_buffer(
        self,
    ) -> PytoyBuffer:
        return self._session_handler.buffer_provider.provide()

    def terminate(self) -> None:
        self._session_handler.terminate()
