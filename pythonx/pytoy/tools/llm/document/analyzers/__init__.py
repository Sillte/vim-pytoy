from pydantic import BaseModel, Field


from typing import Annotated
from pytoy.tools.llm.document.core import LanguageKind
from pytoy_llm.composer import InvocationComposer
from pytoy_llm.composer.models import SystemPromptSpec, OutputSpec
from pytoy_llm.task.models import LLMInvocationSpec


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
    prompt_spec = SystemPromptSpec.from_any(
        name="DocumentProfile",
        output_spec=DocumentProfile,
        intent=("Identify the dominant language of the document, its purpose, and its style."),
        rules=[
            "Base the profile on the provided document.",
            "Distinguish observations from interpretations.",
            "Do not infer unsupported characteristics.",
        ],
        guidance_role=("You are an expert in analyzing documents written in natural and programming languages."),
    )

    return InvocationComposer(prompt_spec).compose_llm_invocation_spec()
