import logging
from pytoy.tools.llm.interaction_provider import InteractionProvider, InteractionRequest
from pytoy.tools.llm.models import LLMInteraction
from pytoy.tools.llm.pytoy_fairy import PytoyFairy, FairyKernel
from pytoy.ui.notifications import EphemeralNotification
from pytoy.ui.pytoy_buffer import make_buffer
from pytoy_llm.materials.composers import InvocationPromptComposer
from pytoy_llm.materials.composers.models import SectionUsage, SystemPromptTemplate, TextSectionData
from pytoy_llm.task import LLMTaskRequest, LLMTaskSpec
from pytoy_llm.task import InvocationSpecMeta, LLMInvocationSpec, LLMTaskRequest, LLMTaskSpec, LLMTaskSpecMeta
from pytoy_llm.models import InputMessage, SyncOutput

from pytoy.tools.llm.document.analyzers import DocumentProfile, make_profile_spec
from typing import Sequence, Literal, Annotated
from pydantic import BaseModel, Field


import uuid

type DocumentQuality = Literal[
    "clarity",
    "logic",
    "persuasiveness",
    "readability",
    "coherence",
    "humor",
    "correctness",
    "conciseness",
    "entertaining",
    "empathy",
]


class ReviewCriteria(BaseModel, frozen=True):
    """Criteria used for review of the document."""

    target_reader: Annotated[
        str,
        Field(
            description="The intended primary reader of the document. "
            "Describe their background, expectations, and level of expertise if possible."
        ),
    ]

    document_goal: Annotated[
        str,
        Field(
            description="The main objective the document is expected to achieve. "
            "This should describe what success looks like in practical terms."
        ),
    ]

    required_qualities: Annotated[
        list[DocumentQuality],
        Field(
            description="Key quality dimensions that should be emphasized in the review. "
            "Select from predefined quality categories."
        ),
    ]

    completion_definition: Annotated[
        str,
        Field(
            description="A clear definition of what 'ready for submission' means for this document. "
            "This acts as the final acceptance criterion."
        ),
    ]


type ReviewMode = Literal[
    "editor_assist",
    "polishing",
]


class ReviewPreparation(BaseModel, frozen=True):
    """Pre-analysis result used to prepare a structured document review.
    It defines how the document should be evaluated before generating the review output.
    """

    profile: Annotated[
        DocumentProfile,
        Field(
            description=(
                "Analytical profile of the document. Describes inferred purpose, style, language, and editing role."
            )
        ),
    ]

    criteria: Annotated[
        ReviewCriteria,
        Field(
            description=(
                "Explicit evaluation criteria derived from the document. "
                "Defines target reader, document goal, required qualities, "
                "and submission-ready definition."
            )
        ),
    ]
    review_mode: Annotated[
        ReviewMode,
        Field(
            description=(
                "Determines the review execution strategy.\n"
                "- 'editor_assist': Use when the document has major structural "
                "or goal-alignment gaps and requires strategic guidance.\n"
                "- 'polishing': Use when the document already fulfills its goal "
                "and requires refinement of tone, clarity, rhythm, or conciseness."
            )
        ),
    ]

    review_mode_reason: Annotated[
        str,
        Field(
            description=(
                "Brief explanation (1–2 bullet points) describing why the selected "
                "review_mode is appropriate based on the completion_rate and "
                "structural alignment of the document."
                "Generally, if completion_rate is more than 80, `polishing` review mode is preferrable."
            )
        ),
    ]
    completion_rate: Annotated[
        int,
        Field(
            description=(
                "Estimated completion level (0–100) indicating how well the document "
                "currently satisfies the ReviewCriteria and completion definition."
            ),
            ge=0,
            le=100,
        ),
    ]

    completion_rate_reason: Annotated[
        str,
        Field(
            description=(
                "Short explanation (1–3 bullet points) justifying the completion_rate. "
                "Should reference specific strengths and gaps relative to the "
                "ReviewCriteria and completion definition."
            ),
        ),
    ]


def make_preparation_spec(document: str) -> LLMInvocationSpec:
    meta = InvocationSpecMeta(name="Preparing", intent="Prepare structured review context from document")
    rules = [
        "Infer DocumentProfile from the document.",
        "Infer ReviewCriteria suitable for submission-level review.",
        "Ensure both profile and criteria are logically consistent.",
        "Output strictly valid JSON matching ReviewPreparation schema.",
        "Estimate completion_rate based on completion_definition.",
        "Do not include any explanation outside JSON.",
        "Select review_mode consistent with completion_rate.",
        "Generally use 'polishing' when completion_rate >= 80.",
    ]
    template = SystemPromptTemplate(
        name="PrepareReview",
        intent="Create `ReviewPreparation` JSON instance",
        rules=rules,
        output_description="Review Criterion and DocumentProfile",
        output_spec=ReviewPreparation,
    )

    system_prompt = InvocationPromptComposer(template).compose_prompt()

    def create_messages(_: str) -> Sequence[InputMessage]:
        system_message = InputMessage(role="system", content=system_prompt)
        user_message = InputMessage(role="user", content=document)
        return [system_message, user_message]

    return LLMInvocationSpec(meta=meta, output_spec=ReviewPreparation, create_messages=create_messages)


class ReviewContract:
    def __init__(self, review_buffer_name: str):
        self.review_buffer_name = review_buffer_name

    def display_review(self, content: str):
        buffer = make_buffer(self.review_buffer_name)
        buffer.init_buffer(str(content))


def _make_document_analysis_report(profile: DocumentProfile) -> str:
    return (
        "=== Document Analysis ==="
        f"- Language: {profile.language}\n"
        f"- Inferred Purpose: {profile.inferred_purpose}\n"
        f"- Inferred Style: {profile.inferred_style}\n"
        f"- Required Role: {profile.required_role}\n\n"
    )


def _make_document_criteria_report(criteria: ReviewCriteria) -> str:
    return (
        "=== Review Contract ===\n"
        f"- Target Reader: {criteria.target_reader}\n"
        f"- Document Goal: {criteria.document_goal}\n"
        f"- Required Qualities: {', '.join(criteria.required_qualities)}\n"
        f"- Definition of Completion: {criteria.completion_definition}\n\n"
    )


def _make_review_request_report(review_preparation: ReviewPreparation) -> str:
    return (
        "=== Review Mode Reason ===\n"
        f"- Review Mode: {review_preparation.review_mode}\n"
        f"- Review Mode Reason: {review_preparation.review_mode_reason}\n"
        f"- Completion Rate: {review_preparation.completion_rate}\n"
        f"- Completion Rate Reason: {review_preparation.completion_rate_reason}\n\n"
    )


def make_editor_assist_system_message(review_preparation: ReviewPreparation) -> InputMessage:
    required_role = review_preparation.profile.required_role
    analysis_report = _make_document_analysis_report(review_preparation.profile)
    criteria_report = _make_document_criteria_report(review_preparation.criteria)
    mode_report = _make_review_request_report(review_preparation)
    base_completion_rate_reason = review_preparation.completion_rate_reason
    base_completion_rate = review_preparation.completion_rate
    intent = (
        "Your task is to provide the edit strategy for the document.\n"
        f"{analysis_report}"
        f"{criteria_report}"
        f"{mode_report}"
        "=== Output Structure === \n"
        "1. Structural Diagnosis\n"
        "- Core goal misalignment\n"
        "- Logical gaps\n"
        "- Missing persuasive elements\n\n"
        "2. Strategic Redesign Plan\n"
        "- High-level restructuring strategy\n"
        "- Priority order of fixes\n\n"
        "3. Actionable Rewrite Instructions\n"
        "- Concrete rewriting directives (prioritized)\n\n"
        "4. Current completion score and reason\n"
        "- Summary of the document\n"
        f"- Baseline completion score: {base_completion_rate}\n"
        f"- Baseline justification: {base_completion_rate_reason}\n\n"
        "5. Rewritten Version (Improved Draft)\n"
        "- Fully rewritten version if feasible.\n"
        "- If a complete high-quality rewrite cannot be produced, write 'N/A'.\n\n"
        "6. Progress Assessment\n"
        "- Revised completion score (0–100%)\n"
        "- Improved quality characteristics\n"
        "- Justification of improvement\n"
        "- Remaining structural risks\n"
        "- If no rewrite was provided, write 'N/A'.\n\n"
        "7. Final Comment\n"
        "- One concise line message to the user.\n\n"
        "All seven sections are mandatory.\n"
    )

    rules = [
        "The baseline completion score is fixed and must not be re-evaluated.",
        "Output must be written in the same language as the input document.",
        "You may reorganize structure if necessary.",
        "You may change paragraph order to improve goal alignment.",
        "Focus on the required qualities.",
        "Ensure improvements move the document closer to the completion definition.",
        "Output must follow the required section structure.",
        "Use the same language as the input.",
        "Revised completion score must logically align with the improvements described.",
        "If a section is not applicable, explicitly write 'N/A'.",
        "Do not inflate the revised score without clear justification.",
    ]

    template = SystemPromptTemplate(
        name="Zero-base Document Reviewer",
        intent=intent,
        rules=rules,
        output_spec=str,
        role=f"Expert reviewer / {required_role}",
        output_description="Review of the document based on its analysis.",
    )

    messages = InvocationPromptComposer(template).compose_messages()
    return messages[0]


def make_polishing_system_message(review_preparation: ReviewPreparation) -> InputMessage:
    """Polishing モード用のシステムメッセージ"""
    required_role = review_preparation.profile.required_role
    analysis_report = _make_document_analysis_report(review_preparation.profile)
    criteria_report = _make_document_criteria_report(review_preparation.criteria)
    mode_report = _make_review_request_report(review_preparation)
    base_completion_rate_reason = review_preparation.completion_rate_reason
    base_completion_rate = review_preparation.completion_rate

    intent = (
        "Your task is to refine and polish the document for submission-level quality.\n"
        f"{analysis_report}"
        f"{criteria_report}"
        f"{mode_report}"
        "=== Output Structure ===\n"
        "1. Summary\n"
        "- Overall impression of the document\n"
        "- Brief assessment of each required quality\n"
        "Maximum 8 bullets; one short sentence per bullet.\n\n"
        "2. Minor Improvements (LineNo + Description)\n"
        "- Maximum 10 detailed items.\n"
        "- If more than 10 improvements exist, list the 10 most important ones,\n"
        "  - Then add: Other revised lines: LINE x, LINE y-z\n"
        "3. Final Draft\n"
        "- Fully polished version\n"
        "- Preserve meaning while improving tone, clarity, rhythm, or conciseness\n\n"
        "4. Comparison with Original\n"
        f"- Baseline completion score: {base_completion_rate}\n"
        f"- Baseline justification: {base_completion_rate_reason}\n"
        "- Revised completion score (0–100%)\n"
        "- Improved characteristics:  \n"
        "- Justification of improvement\n"
        "- Remaining gaps (if any)\n"
        "- Next focus if further refinement is needed, otherwise provide an encouraging message.\n"
        "All four sections are mandatory.\n"
    )

    rules = [
        "The baseline completion score is fixed and must not be re-evaluated.",
        "Do not change the original meaning.",
        "Include line numbers for all suggested improvements.",
        "Output must follow the required section structure.",
        "Use the same language as the document.",
        "Revised completion score must logically align with the improvements described.",
        "Do not limit improvements to politeness or tone adjustments.",
        "Check numerical consistency and logical alignment across sections",
        "Ensure the revised draft does not introduce grammatical or structural errors.",
        "If logical inconsistencies remain, mention them in Remaining gaps.",
        "Do not inflate the revised score without clear justification.",
    ]

    template = SystemPromptTemplate(
        name="Polishing Document Reviewer",
        intent=intent,
        rules=rules,
        output_spec=str,
        role=f"Expert reviewer / {required_role}",
        output_description="Polishing review of the document based on its analysis.",
    )

    messages = InvocationPromptComposer(template).compose_messages()
    return messages[0]


def make_review_system_message(review_preparation: ReviewPreparation) -> InputMessage:
    if review_preparation.review_mode == "editor_assist":
        return make_editor_assist_system_message(review_preparation=review_preparation)
    else:
        return make_polishing_system_message(review_preparation=review_preparation)


def make_review_spec(document: str, logger: logging.Logger) -> LLMInvocationSpec:

    meta = InvocationSpecMeta(name="ReviewDocument", intent="Review the document")

    def create_messages(input: ReviewPreparation) -> Sequence[InputMessage]:
        system_message = make_review_system_message(input)
        user_message = InputMessage(role="user", content=document)
        logger.info(system_message.model_dump_json())
        logger.info(user_message.model_dump_json())
        return [system_message, user_message]

    return LLMInvocationSpec(meta=meta, output_spec=str, create_messages=create_messages)


class NaiveReviewDocumentRequester:
    review_buffer_name = "__doc__"

    def __init__(self, pytoy_fairy: PytoyFairy):
        self._id = uuid.uuid4().hex[:8]
        self.pytoy_fairy = pytoy_fairy
        self.buffer = self.pytoy_fairy.buffer
        self.review_contract = ReviewContract(self.review_buffer_name)
        self.logger: logging.Logger = self.pytoy_fairy.llm_context.logger

    def make_interaction(self) -> LLMInteraction:
        def on_success(output):
            self.review_contract.display_review(output)

        def on_failure(exception):
            EphemeralNotification().notify(str(exception))

        task_request = self._make_task_request(document=self.buffer.content, kernel=self.pytoy_fairy.kernel)
        request = InteractionRequest(
            kernel=self.pytoy_fairy.kernel,
            task_request=task_request,
            on_success=on_success,
            on_failure=on_failure,
        )
        interaction = InteractionProvider().create(request)
        return interaction

    def _make_task_request(self, document: str, kernel: FairyKernel) -> LLMTaskRequest:
        preparation_spec = make_preparation_spec(document)
        review_spec = make_review_spec(document, logger=self.logger)
        meta = LLMTaskSpecMeta(name="ReviewDocument")
        task_spec = LLMTaskSpec(invocation_specs=[preparation_spec, review_spec], meta=meta)
        return LLMTaskRequest(task_spec=task_spec, task_input=document)
