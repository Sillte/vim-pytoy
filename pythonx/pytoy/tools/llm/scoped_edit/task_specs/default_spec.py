import re
from typing import Literal, Self

from pytoy_llm.composer import InvocationComposer, OutputSpec, SystemPromptSpec
from pytoy_llm.models import LLMMessage, LLMToolsLike
from pytoy_llm.task.models import (
    AgentInvocationSpec,
    FunctionInvocationSpec,
    InvocationSpecMeta,
    LLMInvocationSpec,
    TaskSpec,
    TaskSpecMeta,
)
from pytoy_llm.tools.workspace_explorer import WorkspaceExplorer

from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.tool_execution.execution_environment import EnvironmentManager
from pytoy.tools.llm.scoped_edit.contract import ScopedEditLLMContract
from pytoy.tools.llm.scoped_edit.task_specs.edit_rules import CompletionRuleSet, LanguageRuleSet, StyleRuleSet

type LanguageKind = Literal["python", "english", "japanese"]


def select_language_kind(document: str) -> LanguageKind:
    ...
    if not document.strip():
        return "english"

    # --- 1. Python detection ---
    python_patterns = [
        r"\bdef\b",
        r"\bclass\b",
        r"\bimport\b",
        r"\bfrom\b",
        r"\breturn\b",
        r"if __name__",
        r":\s*$",
        r"```",
    ]

    python_hits = sum(bool(re.search(p, document, re.MULTILINE)) for p in python_patterns)
    if python_hits >= 2:
        return "python"

    # --- 2. Japanese detection ---
    japanese_chars = re.findall(r"[\u3040-\u30FF\u4E00-\u9FFF]", document)
    ratio = len(japanese_chars) / max(len(document), 1)

    if ratio > 0.15:
        return "japanese"

    # --- 3. Default to English ---
    return "english"


class DefaultScopedEditTaskMaker:
    def __init__(self, tools: LLMToolsLike | None = None):
        self._tools = tools

    @classmethod
    def from_buffer(cls, buffer: PytoyBuffer) -> Self:
        if not buffer.is_file:
            return cls(tools=None)
        workspace = EnvironmentManager().find_workspace(start_path=buffer.file_path, preference="auto")
        if workspace:
            return cls(tools=[WorkspaceExplorer.from_any(workspace)])
        return cls(tools=None)

    def make_task(self, document: str, contract: ScopedEditLLMContract) -> TaskSpec:
        select_language_spec = FunctionInvocationSpec.from_any(select_language_kind)
        edit_spec = self._make_scoped_edit_spec(document, contract)
        meta = TaskSpecMeta(name="ScopedEditDocument")
        return TaskSpec.from_specs(invocation_specs=[select_language_spec, edit_spec], meta=meta)

    def _make_scoped_edit_spec(
        self,
        document: str,
        llm_contract: ScopedEditLLMContract,
    ) -> LLMInvocationSpec | AgentInvocationSpec:
        name = "Edit or generation of the part of document inside markers"
        output_description = "A part of the document, focusing on the specified scope between markers."

        def create_message(language_kind: LanguageKind) -> LLMMessage:
            language = language_kind
            guidance_role = "An expert writer and editor"
            intent = "Recontruction of the part of the document while preserving intent, structure, and coherence."
            language_ruleset = LanguageRuleSet.from_document_kind(language)
            style_ruleset = StyleRuleSet.from_language_and_uniformity_mode(language, "structure")
            completion_ruleset = CompletionRuleSet.from_completion_mode(completion_mode="conservative")

            rules = [
                *language_ruleset.rules,
                *llm_contract.rules,
                *style_ruleset.rules,
                *completion_ruleset.rules,
                *llm_contract.override_rules,
            ]

            system_prompt = SystemPromptSpec.from_any(
                name=name,
                output_spec=OutputSpec(output_type=str, description=output_description),
                intent=intent,
                rules=rules,
                guidance_role=guidance_role,
            )
            composer = InvocationComposer(system_prompt)
            supplementary_sections = None
            return composer.compose_message(user_prompt=document, supplementary_sections=supplementary_sections)

        meta = InvocationSpecMeta(name=name, intent="Scoped edit of the document.")
        if self._tools is None:
            return LLMInvocationSpec.from_any(
                create_messages=create_message,
                output_type=str,
                meta=meta,
            )
        else:
            return AgentInvocationSpec.from_any(
                create_messages=create_message, output_type=str, meta=meta, tools=self._tools
            )
