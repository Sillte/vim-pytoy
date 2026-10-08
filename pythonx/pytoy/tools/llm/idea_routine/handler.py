from pathlib import Path
from typing import Self

from pytoy_llm.idea import IdeaSpace

from pytoy.shared.timertask.routine_session import (
    RoutineContext,
    RoutineSessionHandler,
    RoutineSessionRequest,
    RoutineUnitHooks,
    RoutineUnitRequest,
)
from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery, LLMSessionRequest

from .driver import IdeaRoutineDriver


class IdeaRoutineHandler:
    kind = IdeaRoutineDriver.kind
    buffer_name = "__idea-routine__"

    def __init__(self, session_handler: LLMSessionHandler, driver: IdeaRoutineDriver) -> None:
        self._session_handler = session_handler
        self._driver = driver

        def _worker(_: RoutineContext) -> None:
            pass

        def _start_llm_progress(_: None) -> None:
            self.session_handler.make_progress("NON-USED INPUT")

        self._routine_session_handler = RoutineSessionHandler.create(request=RoutineSessionRequest(kind=self.kind))
        self._routine_unit_handler = self._routine_session_handler.create_unit(
            request=RoutineUnitRequest(name="llm-invocation", worker=_worker, delay=1000 * 30, max_iteration=300),
            hooks=RoutineUnitHooks.from_any(on_result=_start_llm_progress),
        )
        self._session_handler.on_exit.subscribe(lambda _: self._routine_session_handler.terminate())

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
            if isinstance(session_driver, IdeaRoutineDriver):
                return cls(llm_handler, session_driver)
            else:
                raise RuntimeError("IdeaRoutineDriver is not preserved.")
        existing_handlers = LLMSessionHandler.query(LLMSessionQuery.from_any(kind=cls.kind))
        if existing_handlers:
            raise ValueError(
                "An idea-routine session already exists for different metadata: "
                f"{existing_handlers[0].metadata} != {metadata}"
            )
        driver = IdeaRoutineDriver.from_any(idea_space, workspace=workspace)
        request = LLMSessionRequest.from_any(
            driver=driver,
            buffer_source=BufferSource.from_no_file(name=IdeaRoutineHandler.buffer_name),
            kind=cls.kind,
            metadata=metadata,
            interface="autonomous",
        )
        llm_handler = LLMSessionHandler.create(request)
        try:
            driver.initialize_session()
        except Exception:
            llm_handler.terminate()
            raise
        return cls(llm_handler, driver)

    def start(self) -> None:
        self._routine_unit_handler.start()

    def terminate(self) -> None:
        self._routine_session_handler.terminate()
        self._session_handler.terminate()
