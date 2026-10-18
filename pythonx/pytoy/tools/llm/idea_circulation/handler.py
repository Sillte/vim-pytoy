from pathlib import Path
from typing import Self

from pytoy_llm.idea import IdeaSpace

from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery, LLMSessionRequest
from pytoy.tools.llm.idea_circulation.routines import ValueCycleRoutineHandler

from .buffer_hooks import build_buffer_hooks
from .driver import IdeaCirculationDriver
from .statuses import IdeaCirculationStatus


class IdeaCirculationHandler:
    kind = IdeaCirculationDriver.kind
    buffer_name = "__idea-circulation__"

    def __init__(
        self, session_handler: LLMSessionHandler, driver: IdeaCirculationDriver, idea_routine: ValueCycleRoutineHandler
    ) -> None:
        self._session_handler = session_handler
        self._driver = driver
        self._idea_routine = idea_routine

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
            if not isinstance(session_driver, IdeaCirculationDriver):
                raise RuntimeError("IdeaCirculationDriver is not preserved.")
            status = session_driver.status
            idea_routine = ValueCycleRoutineHandler.from_any(
                session_handler=llm_handler,
                idea_space=idea_space,
                workspace=workspace,
                status=status,
            )
            return cls(llm_handler, session_driver, idea_routine)

        existing_handlers = LLMSessionHandler.query(LLMSessionQuery.from_any(kind=cls.kind))
        if existing_handlers:
            raise ValueError(
                "An idea-circulation session already exists for different metadata: "
                f"{existing_handlers[0].metadata} != {metadata}"
            )
        status = IdeaCirculationStatus(workspace_name=workspace_path.name, value_cycle_working_status="idle")
        driver = IdeaCirculationDriver.from_any(idea_space, workspace=workspace, status=status)
        request = LLMSessionRequest.from_any(
            driver=driver,
            buffer_source=BufferSource.from_no_file(name=IdeaCirculationHandler.buffer_name),
            kind=cls.kind,
            metadata=metadata,
            buffer_hooks=build_buffer_hooks(idea_space),
        )
        llm_handler = LLMSessionHandler.create(request)
        idea_routine = ValueCycleRoutineHandler.from_any(
            session_handler=llm_handler,
            idea_space=idea_space,
            workspace=workspace,
            status=status,
        )
        return cls(llm_handler, driver, idea_routine)

    def start(self) -> None:
        self._idea_routine.start()
        self._session_handler.buffer_provider.provide()

    def terminate(self) -> None:
        self._idea_routine.terminate()
        self._session_handler.terminate()
