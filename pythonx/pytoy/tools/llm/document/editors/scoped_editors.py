import logging
import re

from typing import Sequence
from pytoy.ui.notifications import EphemeralNotification
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_window import CharacterRange

import uuid

from pytoy_llm.materials.composers import InvocationPromptComposer
from pytoy_llm.materials.composers.models import SectionUsage, SystemPromptTemplate
from pytoy_llm.materials.core import ModelSectionData, SectionData
from pytoy_llm.models import InputMessage, SyncOutput
from pytoy_llm.task import InvocationSpecMeta, LLMInvocationSpec, LLMTaskRequest, LLMTaskSpec, LLMTaskSpecMeta, FunctionInvocationSpec

from pytoy.infra.timertask import ThreadWorker
from pytoy.tools.llm.document.analyzers import DocumentProfile, make_profile_spec, LanguageKind
from pytoy.tools.llm.document.editors.edit_rules import LanguageRuleSet, CompletionRuleSet, StyleRuleSet
from pytoy.tools.llm.interaction_provider import InteractionProvider, InteractionRequest
from pytoy.tools.llm.kernel import FairyKernel
from pytoy.tools.llm.models import LLMInteraction
from pytoy.tools.llm.pytoy_fairy import PytoyFairy
from pytoy.tools.llm.references import ReferenceHandler


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


class ScopedReconstructionContract:
    def __init__(self, query_start: str, query_end: str):
        self._query_start = query_start
        self._query_end = query_end

    @classmethod
    def from_id(cls, id_: str | None = None):
        if id_ is None:
            id_ = uuid.uuid4().hex[:8]
        query_start = f"[pytoy-llm][{id_}]>$>"
        query_end = f">$>[pytoy-llm][{id_}]"
        return cls(query_start, query_end)

    @property
    def rules(self) -> Sequence[str]:
        return [
        f"The model's modification authority is strictly limited to the text between `{self.query_start}` and `{self.query_end}`.",
        "The model MUST NOT modify, summarize, or reproduce any text outside this region.",
        f"The output MUST NOT include the markers `{self.query_start}` or `{self.query_end}`.",
        "The output MUST consist solely of the reconstructed content for the scoped region.",
        "When the markers are removed, the resulting document must read as a coherent whole.",
        "The scoped text may be a fragment of a larger document.",
        "If surrounding context exists, stylistic and structural conventions implied by it must be preserved."
    ]
        
    @property
    def override_directive_rules(self) -> Sequence[str]:
        return [
            "**Directive Handling:**",
            "- If the first non-empty line inside the markers starts with one or more `@`, treat that line as a directive and DO NOT include it in the output.",
            "- The number of consecutive `@` characters defines its strength:",
            "    - @: weak directive (lower priority than the other rules.).",
            "    - @@, @@@, @@@@ or more: absolute directive (redefines the reconstruction objective and strategy within the scoped boundary).",
            "- Directives may redefine task intent, tone, or structural goals, but they MUST NOT violate the scoped boundary contract.",
            "- Directives cannot authorize modification of text outside the markers.",
            "- The directive line MUST be completely removed before reconstruction begins."
        ]


    def insert_markers(self, buffer: PytoyBuffer, selection: CharacterRange) -> None:
        text = buffer.get_text(selection)
        new_text = f"{self.query_start}\n{text}\n{self.query_end}"
        buffer.range_operator.replace_text(selection, new_text)

    def revert_markers(self, buffer: PytoyBuffer) -> None:
        start_range = buffer.range_operator.find_first(self.query_start)
        if start_range:
            buffer.range_operator.replace_text(start_range, "")
        end_range = buffer.range_operator.find_first(self.query_end)
        if end_range:
            buffer.range_operator.replace_text(end_range, "")

    def override_target(self, buffer: PytoyBuffer, content: str) -> None:
        """Based on the contract with LLM,  `content` should be the texgt within markers.
        Unfortunately, if content includes `markers`, then the inside of markers becomes the `target`.
        """
        content = self._recover_edit_target(content)
        start_range = buffer.range_operator.find_first(self.query_start)
        end_range = buffer.range_operator.find_first(self.query_end)

        if not start_range or not end_range:
            EphemeralNotification().notify("Request is gone, so no operations.")
            return
        cr = CharacterRange(start_range.start, end_range.end)
        buffer.range_operator.replace_text(cr, content)

    def _recover_edit_target(self, content: str) -> str:
        lines = content.replace("\r\n", "\n").split("\n")
        lines = [line.strip(" ") for line in lines]
        s_index, e_index = None, None
        for i, line in enumerate(lines):
            if line.find(self.query_start.strip()) == 0:
                s_index = i
                break
        for i in reversed(range(len(lines))):
            line = lines[i]
            if line.find(self.query_end.strip()) == 0:
                e_index = i
                break
        if s_index is not None and e_index is not None and s_index < e_index:
            output_in_concern = "\n".join(lines[s_index + 1: e_index])
        else:
            output_in_concern = content
        return output_in_concern

    @property
    def query_start(self) -> str:
        return self._query_start

    @property
    def query_end(self) -> str:
        return self._query_end


def make_scoped_edit_spec(document: str, scoped_edit_contract: ScopedReconstructionContract, reference_handler: ReferenceHandler, logger: logging.Logger) -> LLMInvocationSpec:
    """Based on the `DocumentAnalysis`. provide the edit."""
    def _make_user_prompt(document: str) -> InputMessage:
        return InputMessage(role="user", content=document)

    user_message = _make_user_prompt(document)
    name = "Edit or generation of the part of document inside markers"
    output_description = "A part of the document, focusing on the specified scope between markers."

    def create_messages(language_kind: LanguageKind) -> list[InputMessage]:
        language = language_kind
        role = "An expert writer and editor"
        intent = "Recontruction of the part of the document while preserving intent, structure, and coherence."
        language_ruleset= LanguageRuleSet.from_document_kind(language)
        style_ruleset= StyleRuleSet.from_language_and_uniformity_mode(language, "structure")
        completion_ruleset = CompletionRuleSet.from_completion_mode(completion_mode="conservative")
        
    
        rules = [
            *language_ruleset.rules,
            *scoped_edit_contract.rules,
            *style_ruleset.rules,
            *completion_ruleset.rules,
            *scoped_edit_contract.override_directive_rules,
        ]

        system_prompt = SystemPromptTemplate(
            name=name,
            output_spec=str,
            intent=intent,
            rules=rules,
            role=role,
            output_description=output_description,
        )


        composer = InvocationPromptComposer(prompt_template=system_prompt)
        system_message = InputMessage(role="system", content=composer.compose_prompt())
        logger.info(system_message.model_dump_json())
        logger.info(user_message.model_dump_json())
        return [system_message, user_message]

    return LLMInvocationSpec(
        create_messages=create_messages,
        output_spec=str,
        meta=InvocationSpecMeta(name=name, intent="Scoped edit of the document."),
    )


class ScopedEditDocumentRequester:
    def __init__(self, pytoy_fairy: PytoyFairy):
        self._id = uuid.uuid4().hex[:8]
        self.scoped_edit_contract = ScopedReconstructionContract.from_id(self._id)
        self.pytoy_fairy = pytoy_fairy

    @property
    def query_start(self) -> str:
        return f"[pytoy-llm][{self._id}]>$>"

    @property
    def query_end(self) -> str:
        return f">$>[pytoy-llm][{self._id}]"

    def _apply_output(self, buffer: PytoyBuffer, output: SyncOutput) -> None:
        output_str = str(output)
        logger = self.pytoy_fairy.kernel.llm_context.logger
        logger.info(str(output))
        self.scoped_edit_contract.override_target(buffer, output_str)

    def _handle_error(self, buffer: PytoyBuffer, exception: Exception) -> None:
        self.scoped_edit_contract.revert_markers(buffer)
        ThreadWorker.add_message(str(exception))
        EphemeralNotification().notify("LLM Error. See `:messages`.")

    def make_interaction(self) -> LLMInteraction:
        buffer = self.pytoy_fairy.buffer
        kernel = self.pytoy_fairy.kernel
        self.scoped_edit_contract.insert_markers(buffer, self.pytoy_fairy.selection)

        document = buffer.content
        task_request = self._make_task_request(document, kernel)

        request = InteractionRequest(
            kernel=kernel,
            task_request=task_request,
            on_success=lambda output: self._apply_output(buffer, output),
            on_failure=lambda exc: self._handle_error(buffer, exc),
        )
        return InteractionProvider().create(request)

    def _make_task_request(self, document: str, kernel: FairyKernel) -> LLMTaskRequest:
        select_language_spec = FunctionInvocationSpec.from_any(select_language_kind)
        edit_spec = make_scoped_edit_spec(document, self.scoped_edit_contract, kernel.llm_context.reference_handler, self.pytoy_fairy.kernel.llm_context.logger)
        meta = LLMTaskSpecMeta(name="ScopedEditDocument")
        task_spec = LLMTaskSpec(invocation_specs=[select_language_spec, edit_spec], meta=meta)
        return LLMTaskRequest(task_spec=task_spec, task_input=document)