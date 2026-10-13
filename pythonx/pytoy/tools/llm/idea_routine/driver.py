import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, ClassVar, Literal, Self

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMRequest, LLMRequestLike, LLMTokens
from pytoy_llm.task.models import AgentInvocationSpec, ExecutionContext, InvocationHooks, TaskSpec
from pytoy_llm.tools.idea_tool import IdeaTool
from pytoy_llm.tools.workspace_explorer import WorkspaceExplorer

from pytoy.shared.lib.outcome import is_error
from pytoy.shared.pytoy_configuration import PytoyConfiguration
from pytoy.shared.ui import PytoyBuffer
from pytoy.tool_execution.llm import LLMExecutionExit, LLMExecutionHandler
from pytoy.tool_session.llm import (
    LLMMessageLike,
    LLMSessionBufferHooks,
    LLMSessionBufferProvider,
    LLMSessionDriverProtocol,
    TaskRequest,
)

from .body_codec import BufferBodyCodec
from .metadata_codec import BufferMetadataCodec
from .prompts import BASE_SYSTEM_PROMPT, CONVENTION, SYSTEM_PERSONALITY
from .values.tools import ValuableDemandProviderTool

EXCEPTION_LOG_FOLDER_NAME = "exceptions"
RESPONSE_LOG_FOLDER_NAME = "responses"
MASTER_FOLDER_NAME = "master"
INITIAL_USER_INTENT = """
# Initial User Intent

No explicit user intent has been recorded yet.

When proposing valuable work, consider relevant existing materials
in the IdeaSpace and the available workspace. Do not treat inferred
interests as explicit user intentions.

---
## To the User

Please describe your intentions in this file.
""".strip()


def _construct_system_prompt(idea_space: IdeaSpace) -> str:
    base_system_prompt_path = idea_space.root_space.space_meta_folder / "base_system_prompt.md"
    system_personality_path = idea_space.root_space.space_meta_folder / "system_personality.md"
    if base_system_prompt_path.exists():
        base_system_prompt = base_system_prompt_path.read_text(encoding="utf8")
    else:
        base_system_prompt_path.write_text(BASE_SYSTEM_PROMPT, encoding="utf8")
        base_system_prompt = BASE_SYSTEM_PROMPT

    if system_personality_path.exists():
        system_personality = system_personality_path.read_text(encoding="utf8")
    else:
        system_personality_path.write_text(SYSTEM_PERSONALITY, encoding="utf8")
        system_personality = SYSTEM_PERSONALITY

    return "\n\n".join([elem.strip() for elem in [base_system_prompt, system_personality]])


def _make_task_spec(
    idea_space: IdeaSpace,
    workspace: Path | None = None,
) -> TaskSpec:

    def _create_request(llm_message: LLMMessageLike | None, _context: ExecutionContext) -> LLMRequestLike:
        system_prompt = _construct_system_prompt(idea_space=idea_space)
        new_messages = LLMRequest.from_any(llm_message).messages if llm_message is not None else ()
        return LLMRequest.from_any(new_messages, system_prompt=system_prompt)

    if workspace is None:
        workspace = idea_space.root_folder_path
    idea_tool = IdeaTool.from_any(idea_space_roots=idea_space.root_folder_path, workspace_root=workspace)
    workspace_explorer = WorkspaceExplorer.from_any(workspace=workspace, ignored_roots=[idea_space.root_folder_path])
    hooks = InvocationHooks.from_any(
        on_start=lambda _: idea_tool.mark_llm_start(), on_completion=lambda _: idea_tool.mark_llm_finished()
    )
    demand_provider = ValuableDemandProviderTool.from_any(idea_space.root_folder_path)

    tools = [
        *idea_tool.tools,
        *workspace_explorer.tools,
        *demand_provider.tools,
    ]
    spec = AgentInvocationSpec.from_any(
        create_request=_create_request,
        output_type=str,
        tools=tools,
        hooks=hooks,
    )

    return TaskSpec.from_specs(
        [spec],
    )


type RoutineStatus = Literal["idle", "working"]


class IdeaRoutineDriver(LLMSessionDriverProtocol):
    kind: ClassVar[str] = "idea-routine"

    def __init__(self, idea_space: IdeaSpace, workspace: Path | None, *, logger: logging.Logger | None = None) -> None:
        self._idea_space = idea_space
        self._workspace = workspace
        self._routine_status: RoutineStatus = "idle"
        self._llm_tokens = LLMTokens(prompt=0, completion=0, total=0, cache_read=0, cache_write=0)
        self._logger = logger or PytoyConfiguration().get_logger(location="global", level=logging.INFO)

    @classmethod
    def from_any(cls, idea_space_folder: str | Path | IdeaSpace, workspace: Path | None = None) -> Self:
        if not isinstance(idea_space_folder, IdeaSpace):
            idea_space = IdeaSpace.from_path(path=idea_space_folder, with_creation=True)
        else:
            idea_space = idea_space_folder
        return cls(idea_space=idea_space, workspace=workspace)

    def initialize_session(self) -> None:
        self._prepare_idea_space()

    def make_progress(
        self,
        execution_creator: Callable[[TaskRequest], LLMExecutionHandler],
        llm_buffer_provider: LLMSessionBufferProvider,
        llm_message: LLMMessageLike | None,
    ) -> None:
        task_spec = _make_task_spec(self._idea_space, workspace=self._workspace)
        task_request = TaskRequest(spec=task_spec, input=llm_message)

        execution_handler = execution_creator(task_request)
        execution_handler.on_exit.subscribe(
            lambda exit_entity: self.on_exit(exit_entity, llm_buffer_provider=llm_buffer_provider)
        )
        execution_handler.start()

        self._routine_status = "working"
        buffer = llm_buffer_provider.provide()
        self.update_buffer(buffer)

    def on_exit(self, exit_entity: LLMExecutionExit, llm_buffer_provider: LLMSessionBufferProvider) -> None:
        if is_error(exit_entity.outcome):
            exception = exit_entity.outcome.exception
            try:
                log_folder = self.idea_space.root_space.space_meta_directory / EXCEPTION_LOG_FOLDER_NAME
                log_folder.mkdir(exist_ok=True, parents=True)
                log_file = log_folder / f"{datetime.now():%Y%m%d_%H%M%S}_exception.txt"
                log_file.write_text(str(exception))
            except OSError:
                pass
        else:
            result = exit_entity.outcome.value
            self._llm_tokens = LLMTokens.aggregate((self._llm_tokens, result.task_result.llm_tokens))
            try:
                response_folder = self.idea_space.root_space.space_meta_directory / RESPONSE_LOG_FOLDER_NAME
                response_folder.mkdir(exist_ok=True, parents=True)
                response_file = response_folder / f"{datetime.now():%Y%m%d_%H%M%S}_response.txt"
                response_file.write_text(str(result.output))
            except OSError:
                pass

        self._routine_status = "idle"
        buffer = llm_buffer_provider.provide()
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

    @classmethod
    def build_buffer_hooks(cls, idea_space: IdeaSpace) -> LLMSessionBufferHooks:
        # TODO: We have to condier the special handling of the links based on the `idea_space`
        actions = dict()

        def on_creation(buffer):
            buffer.metadata.data["idea-space"] = idea_space

        return LLMSessionBufferHooks(actions=actions, on_creation=on_creation)

    @property
    def idea_space(self) -> IdeaSpace:
        return self._idea_space

    @property
    def folder_path(self) -> Path:
        return self.idea_space.folder_path

    def _prepare_idea_space(self) -> None:
        convention_path = self.folder_path / ".convention.md"
        master_folder_path = self.folder_path / MASTER_FOLDER_NAME
        if not self.folder_path.exists():
            self.folder_path.mkdir(exist_ok=True, parents=True)
        if not convention_path.exists():
            convention_path.write_text(CONVENTION, encoding="utf8")

        master_folder_path.mkdir(exist_ok=True, parents=True)

        initial_intent_path = master_folder_path / "intentions.md"
        if not initial_intent_path.exists():
            initial_intent_path.write_text(
                INITIAL_USER_INTENT,
                encoding="utf-8",
            )
