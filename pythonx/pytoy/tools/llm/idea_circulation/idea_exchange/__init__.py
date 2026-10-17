from pathlib import Path
from typing import Annotated, Literal, Sequence

from pydantic import BaseModel, Field
from pytoy_llm.idea import IdeaSpace
from pytoy_llm.materials.models import JsonMaterialData
from pytoy_llm.models import LLMRequest, LLMRequestLike
from pytoy_llm.models.llm_messages import LLMMessageLike
from pytoy_llm.task.models import AgentInvocationSpec, ExecutionContext, InvocationHooks
from pytoy_llm.tools.idea_tool import IdeaTool
from pytoy_llm.tools.idea_tool.models import IdeaNotePath
from pytoy_llm.tools.workspace_explorer import WorkspaceExplorer

from .prompts import BASE_SYSTEM_PROMPT, SYSTEM_PERSONALITY


def _construct_system_prompt(idea_space: IdeaSpace) -> str:
    base_system_prompt_path = idea_space.root_space.space_meta_folder / "idea_exchange_system_prompt.md"
    system_personality_path = idea_space.root_space.space_meta_folder / "idea_exchange_system_personality.md"
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


def make_idea_exchange_spec(
    idea_space: IdeaSpace,
    workspace: Path | None = None,
) -> AgentInvocationSpec[str]:

    def _create_request(llm_message: LLMMessageLike, _context: ExecutionContext) -> LLMRequestLike:
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
    tools = [
        *idea_tool.tools,
        *workspace_explorer.tools,
    ]
    return AgentInvocationSpec.from_any(
        create_request=_create_request,
        output_type=str,
        tools=tools,
        hooks=hooks,
    )
