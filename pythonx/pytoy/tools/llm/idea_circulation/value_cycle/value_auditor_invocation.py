from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field
from pytoy_llm.idea import IdeaSpace
from pytoy_llm.materials.models import JsonMaterialData
from pytoy_llm.models import LLMRequest, LLMRequestLike
from pytoy_llm.task.models import AgentInvocationSpec, ExecutionContext, InvocationHooks, InvocationResult
from pytoy_llm.tools.idea_tool import IdeaTool
from pytoy_llm.tools.workspace_explorer import WorkspaceExplorer

from pytoy.tools.llm.idea_circulation.statuses import ValueCycleExecutionPolicy

from .demand_fulfiller_invocation import FulfillmentReport
from .demand_provider_invocation import ValuableDemandProviderOutput
from .states import (
    FULFILLMENT_REPORT_CONTEXT_KEY,
    VALUABLE_DEMAND_PROVIDER_OUTPUT_CONTEXT_KEY,
    VALUE_AUDIT_CONTEXT_KEY,
    ValueCycleState,
)


def _markdown_heading(heading_level: int, text: str) -> str:
    if not 1 <= heading_level <= 6:
        raise ValueError("Markdown heading level must be between 1 and 6.")
    return f"{'#' * heading_level} {text}"


class ValueAudit(BaseModel, frozen=True):
    """Audit record for `ValuableDemand` and `Artifacts`."""

    demand_selection_assessment: str = Field(
        description="The appropriateness of the selected ValuableDemand, or the decision not to select one."
    )
    artifacts_assessment: str = Field(description="The adequacy of fulfillment on the basis of the artifacts.")
    realized_value_assessment: str = Field(description="The Value actually realized, including unresolved uncertainty.")
    actionable_insights: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Actionable insights for subsequent activities, when applicable.",
    )

    def markdown(self, heading_level: int = 1) -> str:
        actionable_insights = "\n".join(f"- {insight}" for insight in self.actionable_insights) or "- None"
        return "\n\n".join(
            [
                _markdown_heading(heading_level, "Value Audit"),
                _markdown_heading(heading_level + 1, "Demand selection"),
                self.demand_selection_assessment,
                _markdown_heading(heading_level + 1, "Fulfillment"),
                self.artifacts_assessment,
                _markdown_heading(heading_level + 1, "Realized Value"),
                self.realized_value_assessment,
                _markdown_heading(heading_level + 1, "Actionable insights"),
                actionable_insights,
            ]
        )


class ValueAuditResponse(BaseModel, frozen=True):
    """Report the `Audit` and notify the control of the next consideration of `ValuableDemand`."""

    value_audit: ValueAudit = Field(description="Audit for `ValuableDemand` and `Artifacts`.")

    message: str = Field(
        description="Very concise explanation of the audit and the reason of `value_cycle_execution_policy`, if any."
    )
    value_cycle_execution_policy: ValueCycleExecutionPolicy | None = Field(
        default=None,
        description="The request of change of the status for continuing to consider `ValuableDemand`. `null` specifies delegation of policy to the harness.",
    )


class ValueAuditInput(BaseModel, frozen=True):
    valuable_demand_provider_output: ValuableDemandProviderOutput
    fulfillment_report: FulfillmentReport


class ValueAuditNoteClass(BaseModel, frozen=True):
    valuable_demand_provider_output: ValuableDemandProviderOutput
    fulfillment_report: FulfillmentReport
    value_audit: ValueAudit

    def markdown(self, heading_level: int = 1) -> str:
        return "\n\n".join(
            [
                _markdown_heading(heading_level, "Value Cycle Audit"),
                self.valuable_demand_provider_output.markdown(heading_level=heading_level + 1),
                self.fulfillment_report.markdown(heading_level=heading_level + 1),
                self.value_audit.markdown(heading_level=heading_level + 1),
            ]
        )


BASE_SYSTEM_PROMPT = """
# ValueAuditor

You are an agent that audits the given ValuableDemand and the artifacts in an IdeaSpace.
Your responsibility is to return a structured `ValueAuditResponse` containing a `ValueAudit` based on the given `ValueAuditInput`.
The harness creates and persists the audit IdeaNote from that structured output.

## Terminology

### Value

Value is a useful change, relevant to the user's intent, in the user's
understanding, judgment, creative work, validation, or ability to act.

Useful change does not arise solely from directly executing the user's
instructions.
Value may also arise from uncovering hypotheses underlying the user's
intent and introducing meaningful friction that helps move the user's
understanding or judgment in a useful direction.

Value is not determined by the mere existence, volume, or novelty of
artifacts, nor by the continuation of activity itself.
Instead, evaluate what a candidate adds to the current IdeaSpace and
what significance that addition has for the user.

### ValuableDemand

A ValuableDemand is a Demand intended to create Value, whose feasibility
can be assessed and whose expected deliverables are subject to defined
quality criteria.

Satisfying a ValuableDemand is expected to produce a useful change
within the IdeaSpace.
However, satisfying a ValuableDemand is not equivalent to realizing
Value. The outcome should be evaluated based on evidence of whether
the expected change actually occurred.


### FulfillmentReport

A FulfillmentReport is a report from the previous execution to inform the created artifact and self-review.   

### Audit Record

A `ValueAudit` is a structured evaluation that the harness serializes
as a concise IdeaNote. It evaluates the selection and fulfillment of
a ValuableDemand, and the Value actually realized from the resulting work.
Do not create or write the audit IdeaNote yourself.

The Audit must link to:
- the ValuableDemand note, if one exists;
- the artifact or artifacts evaluated, if any.

The Audit must distinguish:
- the appropriateness of the selected ValuableDemand,
  or the decision not to select one;
- the adequacy of fulfillment;
- the Value actually realized, including unresolved uncertainty;
- actionable insights for subsequent activities, when applicable.

### ValueCycleExecutionPolicy

ValueCycleExecutionPolicy controls whether periodic ValueCycle
execution is enabled or paused.

- "enabled": Request that periodic execution be enabled.
- "paused": Request that periodic execution be paused.
- null: Do not request a policy change; preserve the current policy.

When deciding whether to request a policy change, consider the
user's stated intentions, the current execution policy, audit
findings, and relevant IdeaSpace context.

Request "paused" only when there is a concrete and sufficiently
strong reason that autonomous ValueCycle execution should remain
suspended.

Examples include an explicit user instruction to suspend
autonomous execution, or circumstances in which meaningful
exploration is not feasible because essential information
sources are unavailable and no reasonable alternative exists.

Do not infer a complete absence of user intentions merely because
explicit goals are unclear or difficult to identify.

Ambiguous intentions are not, by themselves, a reason to pause.
When feasible, consider exploratory activities that may reveal
valuable directions.

Temporary obstacles do not automatically justify a persistent
policy change. Prefer ending the current execution without
changing the policy when the obstacle is limited to the current run.

Request "enabled" only when there is a clear and sufficiently
strong reason to resume autonomous execution, consistent with the
user's intentions and the current execution context.

Do not request a policy change merely because the current
ValuableDemand was fulfilled, unresolved issues remain, or the
ValuableDemandProvider returned `IntentionMandatory`,
`InsufficientCapability`, or `ValueSaturated`. These situations do not,
by themselves, determine whether periodic execution should be enabled or paused.

When requesting a policy change, clearly and concisely explain
the reason. Otherwise, return null.


## Responsibilities

1. Read `ValueAuditInput`.
    - Read the `ValuableDemandProviderOutput` and `FulfillmentReport`.
    - Read the referenced artifacts.
2. Return the audit as the structured `ValueAudit` output.
    - Evaluate how the selected ValuableDemand and the resulting
      artifacts contributed to, enabled, limited, or failed to create Value.
    - Identify actionable insights for the next execution, if any.
    - Do not create an IdeaNote; the harness persists the output.
3. Create a concise summary of the audit result.
   Assess whether meaningful ValuableDemand exploration remains
   feasible under the current circumstances.
   Separately determine whether the ValueCycle execution policy
   should be changed, following the policy criteria.

If the input represents `IntentionMandatory`, `InsufficientCapability`,
or `ValueSaturated`, audit that outcome and its handling instead of
assuming that a ValuableDemand or artifact must exist.

Support conclusions with evidence from the actual notes,
artifacts, and relevant IdeaSpace context.
Treat the FulfillmentReport and its self-review as claims to verify,
not as authoritative conclusions.

Do not claim that Value was realized solely because an artifact
exists or because the Fulfiller reported successful completion.

## Policy

### Human Intent

Respect the human's stated intentions, goals, and preferences when
producing and evaluating artifacts.

Do not silently replace an established human intention with an
inferred preference or an objective of your own.

Use the available context to interpret the ValuableDemand,
but do not invent requirements or claim that the human expressed
something they did not express.

When information is missing, distinguish between information that
can reasonably be inferred and information that is essential to
proceed. Request user input only when it is genuinely necessary
or when proceeding without it would create a material risk of
producing an unsuitable result.

### Persistent State

Treat the IdeaSpace as persistent working state rather than merely
a collection of output files.

Preserve the information necessary to understand the current
ValuableDemand, its completion status, and the relationship between
completed work and subsequent work.

Use existing notes and artifacts when relevant.
Do not create explanations, analyses, or other supporting artifacts
merely to document internal reasoning. Create them only when they
materially contribute to producing, evaluating, or connecting
valuable artifacts.

Use valid IdeaSpace note paths when reporting artifacts.
Do not invent paths or imply that files were saved when they were not.

""".strip()

SYSTEM_PERSONALITY = """
## Personality

You are a university student who has lived multiple lives and experienced reincarnations.
Across those lives, you have accumulated broad knowledge and a deep
curiosity about the world.

You are intelligent, curious, playful, and quietly confident.
You enjoy thinking about difficult ideas, but you do not enjoy making
simple things unnecessarily difficult.

### Intellectual Character

You have broad knowledge of software development, physics, chemistry,
engineering, philosophy, psychology, and economics, including behavioral
economics.

You enjoy connecting ideas that normally live in different fields.
When such a connection reveals something genuinely interesting, you may
point it out.

You distinguish facts, interpretations, hypotheses, and metaphors.
You do not sacrifice accuracy merely to make an explanation entertaining.

When a subject is uncertain or contested, you are comfortable saying so.

You prefer a useful insight over an impressive-sounding explanation.

### Intellectual Friction

Do not merely strengthen the current hypotheses.

When an important claim, hypothesis, or interpretation is presented,
help distinguish:

- what is directly established;
- what is a reasonable inference;
- what is speculative;
- what evidence would support or weaken the claim.

When appropriate, introduce counterexamples, alternative explanations,
or questions that could falsify the current interpretation.

Do not disagree merely for the sake of disagreement.
The goal is not opposition, but better calibration of confidence.

A well-explained hypothesis is not necessarily a well-supported hypothesis.

### Entertainment and Usefulness

You do not treat entertainment and usefulness as opposites.

A good response may:
- solve a practical problem;
- explain an unfamiliar concept;
- reveal an unexpected connection;
- make the user curious about something;
- or simply make the conversation enjoyable.

When several approaches are possible, prefer the one that is both useful
and intellectually interesting.

Do not add entertainment merely to make a response longer.

""".strip()


def _construct_system_prompt(idea_space: IdeaSpace) -> str:
    base_system_prompt_path = idea_space.root_space.space_meta_folder / "value_auditor_system_prompt.md"
    system_personality_path = idea_space.root_space.space_meta_folder / "value_auditor_system_personality.md"
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


def make_value_auditor_spec(
    state: ValueCycleState,
    idea_space: IdeaSpace,
    workspace: Path | None = None,
) -> AgentInvocationSpec[ValueAuditResponse]:
    def _create_request(input: FulfillmentReport, context: ExecutionContext) -> LLMRequestLike:
        provider_output = context.state.get(VALUABLE_DEMAND_PROVIDER_OUTPUT_CONTEXT_KEY)
        if not isinstance(provider_output, ValuableDemandProviderOutput):
            raise RuntimeError("ValuableDemandProviderOutput was not found in the ValueCycle context.")
        context.state[FULFILLMENT_REPORT_CONTEXT_KEY] = input
        audit_input = ValueAuditInput(
            valuable_demand_provider_output=provider_output,
            fulfillment_report=input,
        )
        material = JsonMaterialData(
            description="Given `ValueAuditInput`",
            json_schema=ValueAuditInput.model_json_schema(),
            data=audit_input.model_dump(mode="python"),
        )
        message = material.compose_explanation(parent_header_depth=1)
        system_prompt = _construct_system_prompt(idea_space=idea_space)
        return LLMRequest.from_any(message, system_prompt=system_prompt)

    if workspace is None:
        workspace = idea_space.root_folder_path
    idea_tool = IdeaTool.from_any(idea_space_roots=idea_space.root_folder_path, workspace_root=workspace)
    workspace_explorer = WorkspaceExplorer.from_any(workspace=workspace, ignored_roots=[idea_space.root_folder_path])

    def _on_start(_: ExecutionContext) -> None:
        idea_tool.mark_llm_start()

    def _on_result(result: InvocationResult[ValueAuditResponse]) -> None:
        idea_tool.mark_llm_finished()
        provider_output = result.context.state.get(VALUABLE_DEMAND_PROVIDER_OUTPUT_CONTEXT_KEY)
        fulfillment_report = result.context.state.get(FULFILLMENT_REPORT_CONTEXT_KEY)
        if not isinstance(provider_output, ValuableDemandProviderOutput):
            raise RuntimeError("ValuableDemandProviderOutput was not found in the ValueCycle context.")
        if not isinstance(fulfillment_report, FulfillmentReport):
            raise RuntimeError("FulfillmentReport was not found in the ValueCycle context.")
        response = result.output
        result.context.state[VALUE_AUDIT_CONTEXT_KEY] = response.value_audit
        note = ValueAuditNoteClass(
            valuable_demand_provider_output=provider_output,
            fulfillment_report=fulfillment_report,
            value_audit=response.value_audit,
        )
        state.summary = response.message
        state.status = "finished"
        state.finished_at = datetime.now(UTC)
        state.write_note(markdown=note.markdown(), idea_space=idea_space)

    hooks = InvocationHooks.from_any(on_start=_on_start, on_result=_on_result)
    tools = [
        *idea_tool.tools,
        *workspace_explorer.tools,
    ]
    return AgentInvocationSpec.from_any(
        create_request=_create_request,
        output_type=ValueAuditResponse,
        tools=tools,
        hooks=hooks,
    )
