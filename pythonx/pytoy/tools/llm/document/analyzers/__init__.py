from pydantic import BaseModel, Field


from typing import Annotated
from pytoy.tools.llm.document.core import LanguageKind
from pytoy_llm.materials.composers import InvocationPromptComposer
from pytoy_llm.materials.composers.models import SystemPromptTemplate
from pytoy_llm.models import LLMMessage
from pytoy_llm.task.models import InvocationSpecMeta, LLMInvocationSpec


class DocumentProfile(BaseModel):
    """Analysis result of the document."""

    language: Annotated[LanguageKind, Field(description="The dominant language of the document.")]
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
    intent = (
        "Identify the dominant language of the document (such as English, Japanese, or Python), purpose and style .\n"
    )
    template = SystemPromptTemplate(
        name="DocumentProfile",
        output_type=DocumentProfile,
        intent=intent,
        rules=["The output must be in JSON format matching the DocumentAnalysis model."],
        output_description="The analysis result of the document.",
        role="You are an expert in analyzing documents in natural and program languages.",
    )
    composer = InvocationPromptComposer(template)

    def create_messages(input_text: str) -> LLMMessage:
        return LLMMessage.from_prompt(user=input_text, system=composer.compose_prompt())


    return LLMInvocationSpec(
        create_messages=create_messages,
        output_type=template.output_type,
        meta=InvocationSpecMeta(name=template.name, intent=template.intent),
    )
