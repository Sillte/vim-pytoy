from pathlib import Path
from typing import Literal, Self

from pytoy_llm.idea import IdeaSpace

from pytoy.shared.lib.outcome import is_error
from pytoy.shared.timertask.routine_session import (
    RoutineContext,
    RoutineSessionHandler,
    RoutineSessionRequest,
    RoutineUnitRequest,
)
from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery, LLMSessionRequest

from .driver import IdeaCirculationDriver

type RoutineStatus = Literal["idle", "working"]


class IdeaCirculationHandler:
    kind = IdeaCirculationDriver.kind
    buffer_name = "__idea-circulation__"

    def __init__(self, session_handler: LLMSessionHandler, driver: IdeaCirculationDriver) -> None:
        self._session_handler = session_handler
        self._driver = driver

        def _start_llm_progress(_: RoutineContext) -> None:
            exit_entity = self.session_handler.make_progress().result()
            if is_error(exit_entity.outcome):
                raise exit_entity.outcome.exception

        self._routine_session_handler = RoutineSessionHandler.create(request=RoutineSessionRequest(kind=self.kind))
        self._routine_unit_handler = self._routine_session_handler.create_unit(
            request=RoutineUnitRequest(
                name="llm-invocation", worker=_start_llm_progress, delay=1000 * 30, max_iteration=300
            ),
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
            if isinstance(session_driver, IdeaCirculationDriver):
                return cls(llm_handler, session_driver)
            else:
                raise RuntimeError("IdeaCirculationDriver is not preserved.")
        existing_handlers = LLMSessionHandler.query(LLMSessionQuery.from_any(kind=cls.kind))
        if existing_handlers:
            raise ValueError(
                "An idea-circulation session already exists for different metadata: "
                f"{existing_handlers[0].metadata} != {metadata}"
            )
        driver = IdeaCirculationDriver.from_any(idea_space, workspace=workspace)
        request = LLMSessionRequest.from_any(
            driver=driver,
            buffer_source=BufferSource.from_no_file(name=IdeaCirculationHandler.buffer_name),
            kind=cls.kind,
            metadata=metadata,
            buffer_hooks=driver.build_buffer_hooks(idea_space),
            interface="autonomous",
        )
        llm_handler = LLMSessionHandler.create(request)
        return cls(llm_handler, driver)

    def start(self) -> None:
        self._routine_unit_handler.start()

    def terminate(self) -> None:
        self._routine_session_handler.terminate()
        self._session_handler.terminate()
