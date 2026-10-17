from datetime import datetime
from pathlib import Path
from typing import Self

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMTokens
from pytoy_llm.task.models import TaskRequest

from pytoy.shared.lib.outcome import is_error
from pytoy.shared.timertask.routine_session import (
    RoutineContext,
    RoutineSessionHandler,
    RoutineSessionQuery,
    RoutineSessionRequest,
    RoutineUnitHandler,
    RoutineUnitRequest,
)
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.tool_execution.llm import LLMExecutionExit
from pytoy.tool_session.llm import LLMSessionHandler
from pytoy.tools.llm.idea_circulation.driver import IdeaCirculationDriver
from pytoy.tools.llm.idea_circulation.orchestrator.task_creators import create_value_cycle_task_spec

from .body_codec import BufferBodyCodec
from .metadata_codec import BufferMetadataCodec

EXCEPTION_LOG_FOLDER_NAME = "exceptions"
RESPONSE_LOG_FOLDER_NAME = "responses"


class ValueCycleRoutineHandler:
    kind = IdeaCirculationDriver.kind
    routine_unit = "value_cycle_invocation"

    def __init__(
        self,
        idea_space: IdeaSpace,
        workspace: Path | None,
        session_handler: LLMSessionHandler,
        routine_handler: RoutineSessionHandler,
        unit_handler: RoutineUnitHandler,
    ) -> None:
        self._idea_space = idea_space
        self._workspace = workspace
        self._session_handler = session_handler
        self._routine_handler = routine_handler
        self._unit_handler = unit_handler

    @classmethod
    def from_any(
        cls,
        session_handler: LLMSessionHandler,
        idea_space: IdeaSpace,
        workspace: Path | None = None,
        *,
        delay: int = 1000 * 30,
        max_iteration: int | None = 100,
    ) -> Self:

        def routine_work(_: RoutineContext):
            task_spec = create_value_cycle_task_spec(idea_space, workspace=workspace)
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
        return cls(
            idea_space=idea_space,
            workspace=workspace,
            session_handler=session_handler,
            routine_handler=routine_handler,
            unit_handler=unit_handler,
        )

    def start(self) -> None:
        self._unit_handler.start()

    def terminate(self) -> None:
        self._routine_handler.terminate()

    def on_exit(self, exit_entity: LLMExecutionExit) -> None:
        id_ = exit_entity.id
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            try:
                log_folder = self._idea_space.root_space.space_meta_directory / EXCEPTION_LOG_FOLDER_NAME
                log_folder.mkdir(exist_ok=True, parents=True)
                log_file = log_folder / f"{datetime.now():%Y%m%d_%H%M%S}_{id_}_exception.txt"
                log_file.write_text(str(exception))
            except OSError:
                pass
        else:
            result = exit_entity.outcome.value
            self._llm_tokens = LLMTokens.aggregate((self._llm_tokens, result.task_result.llm_tokens))
            try:
                response_folder = self._idea_space.root_space.space_meta_directory / RESPONSE_LOG_FOLDER_NAME
                response_folder.mkdir(exist_ok=True, parents=True)
                response_file = response_folder / f"{datetime.now():%Y%m%d_%H%M%S}_{id_}_response.txt"
                response_file.write_text(str(result.output))
            except OSError:
                pass

        self._routine_status = "idle"
        buffer = self._session_handler.buffer_provider.provide()
        self.update_buffer(buffer)

    def update_buffer(self, buffer: PytoyBuffer) -> None:
        metadata_codec = BufferMetadataCodec.from_any(
            kind=self.kind,
            workspace_name=self._workspace,
            working_status=self._routine_status,
            llm_tokens=self._llm_tokens,
        )
        patch = metadata_codec.create_patch(buffer.content)
        buffer.range_operator.apply_patch(patch)

        body_codec = BufferBodyCodec.from_any(idea_space=self._idea_space)
        patch = body_codec.create_patch(buffer.content)
        buffer.range_operator.apply_patch(patch)
