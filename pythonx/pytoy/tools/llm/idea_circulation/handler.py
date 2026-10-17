from pathlib import Path
from typing import Literal, Self

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.task.models import TaskRequest

from pytoy.shared.timertask.routine_session import (
    RoutineContext,
    RoutineSessionHandler,
    RoutineSessionQuery,
    RoutineSessionRequest,
    RoutineUnitHandler,
    RoutineUnitRequest,
)
from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery, LLMSessionRequest

from .driver import IdeaCirculationDriver
from .orchestrator.task_creators import make_value_cycle_task_spec

type RoutineStatus = Literal["idle", "working"]


class _IdeaRoutineHandler:
    kind = IdeaCirculationDriver.kind
    routine_unit = "value_cycle_invocation"

    def __init__(
        self,
        session_handler: LLMSessionHandler,
        routine_handler: RoutineSessionHandler,
        unit_handler: RoutineUnitHandler,
    ) -> None:
        self._session_handelr = session_handler
        self._routine_handler = routine_handler
        self._unit_handler = unit_handler

    @classmethod
    def from_any(
        cls,
        session_handler: LLMSessionHandler,
        idea_space: IdeaSpace,
        workspace: Path | None,
        *,
        delay: int = 1000 * 30,
        max_iteration: int | None = 100,
    ) -> Self:

        def routine_work(_: RoutineContext):
            task_spec = make_value_cycle_task_spec(idea_space, workspace=workspace)
            task_request = TaskRequest(spec=task_spec, input=None)
            future = session_handler.execute_task(task_request)
            future.result()

        routine_handlers = RoutineSessionHandler.query(RoutineSessionQuery(kind=cls.kind))
        if routine_handlers:
            routine_handler = routine_handlers[0]
        else:
            routine_handler = RoutineSessionHandler.create(request=RoutineSessionRequest(kind=cls.kind))
            session_handler.on_exit.subscribe(lambda _: routine_handler.terminate())

        unit_handler = routine_handler.get_unit(cls.routine_unit)
        if not unit_handler:
            unit_handler = routine_handler.create_unit(
                request=RoutineUnitRequest(
                    name=cls.routine_unit, worker=routine_work, delay=delay, max_iteration=max_iteration
                )
            )
        return cls(session_handler, routine_handler, unit_handler)

    def start(self) -> None:
        self._unit_handler.start()

    def terminate(self) -> None:
        self._routine_handler.terminate()


class IdeaCirculationHandler:
    kind = IdeaCirculationDriver.kind
    buffer_name = "__idea-circulation__"

    def __init__(
        self, session_handler: LLMSessionHandler, driver: IdeaCirculationDriver, idea_routine: _IdeaRoutineHandler
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
            idea_routine = _IdeaRoutineHandler.from_any(
                session_handler=llm_handler, idea_space=idea_space, workspace=workspace
            )
            if isinstance(session_driver, IdeaCirculationDriver):
                return cls(llm_handler, session_driver, idea_routine)
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
        idea_routine = _IdeaRoutineHandler.from_any(
            session_handler=llm_handler, idea_space=idea_space, workspace=workspace
        )
        return cls(llm_handler, driver, idea_routine)

    def start(self) -> None:
        self._idea_routine.start()

    def terminate(self) -> None:
        self._idea_routine.terminate()
        self._session_handler.terminate()
