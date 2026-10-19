from pathlib import Path
from typing import Self

from pytoy_llm.idea import IdeaSpace

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
from pytoy.tool_execution.llm import (
    LLMExecutionExit,
    LLMExecutionHandler,
    LLMExecutionHooks,
    LLMExecutionRequest,
)
from pytoy.tool_session.llm import LLMSessionHandler
from pytoy.tools.llm.idea_circulation.driver import IdeaCirculationDriver
from pytoy.tools.llm.idea_circulation.orchestrator.task_creators import ValueAuditResponse, create_value_cycle_task_spec

from .metadata_codec import BufferMetadataCodec
from .statuses import IdeaCirculationStatus


class ValueCycleRoutineHandler:
    kind = IdeaCirculationDriver.kind
    routine_unit = "value_cycle_invocation"

    def __init__(
        self,
        idea_space: IdeaSpace,
        workspace: Path | None,
        status: IdeaCirculationStatus,
        session_handler: LLMSessionHandler,
        routine_handler: RoutineSessionHandler,
        *,
        delay: int = 1000 * 30,
        max_iteration: int | None = 100,
    ) -> None:
        self._idea_space = idea_space
        self._workspace = workspace
        self._status = status
        self._session_handler = session_handler
        self._routine_handler = routine_handler
        self._unit_handler = self._construct_unit_handler(
            self._idea_space,
            workspace=self._workspace,
            routine_handler=self._routine_handler,
            delay=delay,
            max_iteration=max_iteration,
        )

    @classmethod
    def from_any(
        cls,
        session_handler: LLMSessionHandler,
        idea_space: IdeaSpace,
        status: IdeaCirculationStatus,
        workspace: Path | None = None,
        *,
        delay: int = 1000 * 30,
        max_iteration: int | None = 100,
    ) -> Self:

        routine_handlers = RoutineSessionHandler.query(RoutineSessionQuery(kind=cls.kind))
        if routine_handlers:
            routine_handler = routine_handlers[0]
        else:
            routine_handler = RoutineSessionHandler.create(request=RoutineSessionRequest(kind=cls.kind))
            session_handler.on_exit.subscribe(lambda _: routine_handler.terminate())

        return cls(
            idea_space=idea_space,
            workspace=workspace,
            status=status,
            session_handler=session_handler,
            routine_handler=routine_handler,
            delay=delay,
            max_iteration=max_iteration,
        )

    def start(self) -> None:
        self._unit_handler.start()

    def terminate(self) -> None:
        self._routine_handler.terminate()

    def _construct_unit_handler(
        self,
        idea_space: IdeaSpace,
        workspace: Path | None,
        routine_handler: RoutineSessionHandler,
        *,
        delay: int,
        max_iteration: int | None = None,
    ) -> RoutineUnitHandler:

        def routine_work(_: RoutineContext):
            if self._status.value_cycle_execution_policy == "paused":
                return
            self._status.value_cycle_working_status = "working"
            task_spec = create_value_cycle_task_spec(idea_space, workspace=workspace)
            request = LLMExecutionRequest.from_any(task_spec=task_spec, input=None)
            future = LLMExecutionHandler.execute(request, hooks=LLMExecutionHooks.from_any(on_exit=self.on_exit))
            future.result()

        unit_handler = routine_handler.get_unit(self.routine_unit)
        if not unit_handler:
            unit_handler = routine_handler.create_unit(
                request=RoutineUnitRequest(
                    name=self.routine_unit, worker=routine_work, delay=delay, max_iteration=max_iteration
                )
            )
        return unit_handler

    def on_exit(self, exit_entity: LLMExecutionExit[ValueAuditResponse]) -> None:
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            self._status.change_value_cycle_message(str(exception))
        else:
            result = exit_entity.outcome.value
            response = result.output

            self._status.update_tokens(result.task_result.llm_tokens)
            self._status.change_value_cycle_message(response.message)
            if response.value_cycle_execution_policy:
                self._status.change_value_cycle_execution_policy(response.value_cycle_execution_policy)

        self._status.value_cycle_working_status = "idle"
        buffer = self._session_handler.buffer_provider.provide()
        self.update_buffer(buffer)

    def update_buffer(self, buffer: PytoyBuffer) -> None:
        metadata_codec = BufferMetadataCodec.from_any(status=self._status)
        patch = metadata_codec.create_patch(buffer.content)
        buffer.range_operator.apply_patch(patch)
