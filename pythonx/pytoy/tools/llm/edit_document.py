from pytoy.infra.timertask import ThreadWorker
import logging

from pytoy.tools.llm.kernel import FairyKernel
from pytoy.tools.llm.interaction_provider import InteractionRequest
from pytoy.tools.llm.interaction_provider import InteractionProvider
from pytoy.tools.llm.models import HooksForInteraction, LLMInteraction

from pytoy.tools.llm.pytoy_fairy import PytoyFairy
from pytoy.ui.notifications import EphemeralNotification
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_window import CharacterRange
from pytoy_llm.materials.composers import InvocationPromptComposer
from pytoy_llm.materials.composers.models import SystemPromptTemplate, SectionUsage
from pytoy_llm.task import LLMTaskSpec, LLMTaskRequest, LLMTaskSpecMeta, InvocationSpecMeta, LLMInvocationSpec
from pytoy_llm.models import InputMessage, SyncOutput
from pytoy_llm.materials.core import SectionData, ModelSectionData
from pytoy.tools.llm.references import ReferenceHandler


import uuid
from pydantic import BaseModel, Field

from typing import Literal, Annotated, Protocol, Sequence, assert_never

type DocumentLanguageType = Literal["python", "english", "japanese"]


class DocumentProfile(BaseModel):
    """Analysis result of the document."""

    language: Annotated[
        DocumentLanguageType, Field(description="The dominant language of the document.")
    ]
    required_role: Annotated[
        str, Field(description="The appropriate role to edit this document, which is easily interpretable by LLM.")
    ]
    inferred_purpose: Annotated[
        str,
        Field(
            description="The purpose of the document as inferred from its content. The length should be 0-2 sentences. The maximum is 1 paragraph."
        ),
    ]
    inferred_style: Annotated[
        str,
        Field(description="The sytle of the document as inferred from its content. The length must be 1-2 sentences."),
    ]
    improvement_suggestion: Annotated[str, Field(description="Advice for revision, which is intended for LLM.")]


def make_profile_spec() -> LLMInvocationSpec:
    intent = "Identify the dominant language of the document (such as English, Japanese, or Python), purpose and style .\n"
    template = SystemPromptTemplate(
        name="DocumentProfile",
        output_spec=DocumentProfile,
        intent=intent,
        rules=["The output must be in JSON format matching the DocumentAnalysis model."],
        output_description="The analysis result of the document.",
        role="You are an expert in analyzing documents in natural and program languages.",
    )
    composer = InvocationPromptComposer(template)

    def create_messages(input_text: str) -> list[InputMessage]:
        system_message = InputMessage(role="system", content=composer.compose_prompt())
        user_message = InputMessage(role="user", content=input_text)
        return [system_message, user_message]

    return LLMInvocationSpec(
        create_messages=create_messages,
        output_spec=template.output_spec,
        meta=InvocationSpecMeta(name=template.name, intent=template.intent),
    )
    

class EditScopeContract:
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
    def edit_scope_intent(self) -> str:
        return (f"- Output the entire document, but only modify the text between `{self.query_start}` and `{self.query_end}`.\n"
                "- After your generation, the evaluation will be based on the full document with markers removed.\n")
    @property
    def edit_scope_rules(self) -> list[str]:
        return [f"The edited document must exist between markers (that is, `{self.query_start}` and `{self.query_end}`).", 
                f"The output must include the markers (that is, `{self.query_start}` and `{self.query_end}`)"]

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
        """If content includes `markers`, then the inside of markers becomes the `target`. 
        If not the entire `content` is written inside `buffer`, the all content becomes the target.
        """
        content = self._normalize_content(content)
        start_range = buffer.range_operator.find_first(self.query_start)
        end_range = buffer.range_operator.find_first(self.query_end)

        if not start_range or not end_range:
            EphemeralNotification().notify("Request is gone, so no operations.")
            return
        cr = CharacterRange(start_range.start, end_range.end)
        buffer.range_operator.replace_text(cr, content)
        
    def _normalize_content(self, content: str) -> str:
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
        

class EditIntent(BaseModel, frozen=True):
    intent: str
    role: str 
    

def make_japanese_intent() -> EditIntent:
    intent = (
        "- 不完全な文や箇条書きは文脈に従って自然に補完せよ\n"
        "- 意図に沿って`...` や `???` などのプレースホルダを最も自然な内容になるように書き換えよ\n"
        "- 表現されている意図や論理構造を尊重せよ\n"
        "- 同一の概念を表す場合は、同一の単語を使用せよ\n"
        "- 箇条書き、番号付きリスト、引用、段落などの階層構造やスタイルを統一せよ\n"
        "- 文末表現（だ／である／です・ます調）を統一せよ\n"
        "- 語彙の硬さ（技術文・説明文・口語）が統一せよ\n"
        "- 連続して読んだときに違和感がないようにせよ\n"
    )
    return EditIntent(intent=intent, role="日本語編集のエキスパート")

def make_english_intent() -> EditIntent:
    intent = (
            "- You are an expert in English writing, ensure natural readability and style consistency.\n"
            "- Before rewriting, consider context outside the markers, sentence completeness, logical flow, and coherence.\n"
            "- Preserve paragraph structure, bullet points, and formatting outside the markers.\n"
            "- Resolve placeholders like '...' or '???' appropriately.\n"
    )
    return EditIntent(intent=intent, role="Expert in English document editing")

def make_python_intent() -> EditIntent:
    intent = (
        "- Preserve coding style: indentation, naming conventions, line breaks, and surrounding structure.\n"
        "- Before editing, consider context outside the markers, code correctness, and logical consistency.\n"
        "- Complete placeholders such as '...' or 'pass' according to surrounding code logic.\n"
        "- Do NOT introduce new abstractions unless explicitly instructed.\n"
    )
    return EditIntent(intent=intent, role="Python code editing expert")

def make_language_intent(language: DocumentLanguageType) -> EditIntent:
    match language:
        case "english":
            return make_english_intent()
        case "japanese":
            return make_japanese_intent()
        case "python":
            return make_python_intent()
        case _: 
            assert_never(language)

def make_edit_spec(document: str, scope_rules: Sequence[str], reference_handler: ReferenceHandler, logger: logging.Logger) -> LLMInvocationSpec:
    """Based on the `DocumentAnalysis`. provide the edit."""
    def _make_user_prompt(document: str) -> InputMessage:
        return InputMessage(role="user", content=document)

    user_message = _make_user_prompt(document)
    name = "Edit Document"
    output_description = "Return the entire document, editing only the text between the markers."

    rules = [
        "Output the entire document, but only modify the text between the markers. Do not alter other content.",
        *scope_rules,
        "The markers must be included; they will be removed after your generation.",
        "Do NOT add explanations, commentary, or meta text.",
        "Prefer similar length unless clarity or correctness requires change.",
        "The rewritten text must read naturally when the markers are removed.",
        "Inside the markers, you MAY organize content into separate lines, bullet points, or numbered items to improve readability.",
        "Inside the markers, you MAY format freely the content.",
        "Line length consistency is a secondary preference and must not override document structure or semantic boundaries.",
    ]

    def create_messages(document_analysis: DocumentProfile) -> list[InputMessage]:
        language = document_analysis.language
        edit_intent = make_language_intent(language)
        role = edit_intent.role 
        if document_analysis.required_role:
            role += f" / {document_analysis.required_role}"
        intent = edit_intent.intent

        system_prompt = SystemPromptTemplate(
            name=name,
            output_spec=str,
            intent=intent,
            rules=rules,
            role=role,
            output_description=output_description,
        )
        logger.info(str(system_prompt))
        section_data_list: list[SectionData] = [ModelSectionData(bundle_kind="DocumentAnalysis", 
                       description="Analysis of the document.",
                       instances=[document_analysis])]
        section_usage_list = [SectionUsage(bundle_kind="DocumentAnalysis",
                                     usage_rule=[
                                         "Use the advice to guide revision.",
                                     ],
                                     )]
        if reference_handler.exist_reference:
            ref_section_writer = reference_handler.section_writer
            section_data_list.append(ref_section_writer.make_section_data())
            section_usage_list.append(ref_section_writer.make_section_usage())

        composer = InvocationPromptComposer(prompt_template=system_prompt,
                                            section_usages=section_usage_list,
                                            section_data_list=section_data_list)
        system_message = InputMessage(role="system", content=composer.compose_prompt())
        return [system_message, user_message]

    return LLMInvocationSpec(
        create_messages=create_messages,
        output_spec=str,
        meta=InvocationSpecMeta(name=name, intent="Edit the document."),
    )


class EditDocumentRequester:
    def __init__(self, pytoy_fairy: PytoyFairy):
        self._id = uuid.uuid4().hex[:8]
        self.editscope_contract = EditScopeContract.from_id(self._id)
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
        self.editscope_contract.override_target(buffer, output_str)

    def _handle_error(self, buffer: PytoyBuffer, exception: Exception) -> None:
        self.editscope_contract.revert_markers(buffer)
        ThreadWorker.add_message(str(exception))
        EphemeralNotification().notify("LLM Error. See `:messages`.")

    def make_interaction(self) -> LLMInteraction:
        buffer = self.pytoy_fairy.buffer
        kernel = self.pytoy_fairy.kernel
        self.editscope_contract.insert_markers(buffer, self.pytoy_fairy.selection)

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
        analysis_spec = make_profile_spec()
        scope_rules = self.editscope_contract.edit_scope_rules
        edit_spec = make_edit_spec(document, scope_rules, kernel.llm_context.reference_handler, self.pytoy_fairy.kernel.llm_context.logger)
        meta = LLMTaskSpecMeta(name="EditDocument")
        task_spec = LLMTaskSpec(invocation_specs=[analysis_spec, edit_spec], meta=meta)
        return LLMTaskRequest(task_spec=task_spec, task_input=document)