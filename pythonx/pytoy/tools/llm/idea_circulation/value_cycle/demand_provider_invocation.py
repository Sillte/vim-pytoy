import time
import uuid
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMRequest, LLMRequestLike
from pytoy_llm.task.models import AgentInvocationSpec, ExecutionContext, InvocationHooks, InvocationResult
from pytoy_llm.tools.idea_tool import IdeaTool
from pytoy_llm.tools.workspace_explorer import WorkspaceExplorer

from pytoy.tool_session.llm import (
    LLMMessageLike,
)

from .states import VALUABLE_DEMAND_PROVIDER_OUTPUT_CONTEXT_KEY, ValueCycleState


def _markdown_heading(heading_level: int, text: str) -> str:
    if not 1 <= heading_level <= 6:
        raise ValueError("Markdown heading level must be between 1 and 6.")
    return f"{'#' * heading_level} {text}"


class ValuableDemand(BaseModel, frozen=True):
    """A demand intended to create Value, with explicit validity conditions and quality criteria."""

    kind: Literal["valuable_demand"] = "valuable_demand"

    summary: str = Field(
        description=(
            "Summary of ValuableDemand. "
            "It is expected to be kebab-case containing only lowercase ASCII letters, digits, and single hyphens. "
            "It is expected to represent the summary of ValuableDemand."
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )

    validity_conditions: str = Field(
        description="Minimum requirements that an artifact must satisfy in order to satisfy the ValuableDemand. Validity has priority over quality."
    )

    quality_criteria: str = Field(
        description="Multiple perspectives from which the value or quality of an artifact may be evaluated."
        " These criteria may conflict with each other, and an artifact does not need to maximize every criterion."
        " Generally, when QualityCriteria conflict,"
        " a clear policy for resolving the trade-off can itself contribute to the perceived quality of the artifact,"
        " because it makes the artifact's concept and intended beneficiary clearer."
    )

    preference: str | None = Field(
        description="Assumptions and evaluation policies of the evaluator and intended audience when they evaluate the quality of the artifact."
    )

    def markdown(self, heading_level: int = 1) -> str:
        sections = [
            _markdown_heading(heading_level, self.summary),
            _markdown_heading(heading_level + 1, "Validity conditions"),
            self.validity_conditions,
            _markdown_heading(heading_level + 1, "Quality criteria"),
            self.quality_criteria,
        ]
        if self.preference is not None:
            sections.extend([_markdown_heading(heading_level + 1, "Preference"), self.preference])
        return "\n\n".join(sections)


class IntentionMandatory(BaseModel, frozen=True):
    """A no-demand outcome used when no grounded direction for valuable exploration is available.

    When conversation, Companion hypotheses, or relevant materials provide a useful direction
    to explore, create a `ValuableDemand` instead.
    """

    kind: Literal["intention_mandatory"] = "intention_mandatory"
    reason_for_no_available_exploration: str = Field(
        description="The reason why the new `ValuableDemand` cannot be created."
    )
    desired_response: str = Field(description=("The action or response needed after this decision."))

    def markdown(self, heading_level: int = 1) -> str:
        return "\n\n".join(
            [
                _markdown_heading(heading_level, "No Valuable Demand (Intention Mandatory)"),
                _markdown_heading(heading_level + 1, "Reason for no available exploration"),
                self.reason_for_no_available_exploration,
                _markdown_heading(heading_level + 1, "Desired response"),
                self.desired_response,
            ]
        )


class InsufficientCapability(BaseModel, frozen=True):
    """A valuable intent cannot be advanced because required capabilities are unavailable.

    Use this only when no feasible alternative activity can advance the intent.
    The intent may be explicit or sufficiently supported by available context.
    """

    kind: Literal["insufficient_capability"] = "insufficient_capability"
    blocked_action: str = Field(description="The action that cannot be performed.")
    required_capabilities: str = Field(description="The tools, permissions, or other capabilities that are missing.")
    suggestion_of_alternative_objectives: str = Field(
        description="Feasible alternative objectives that could be pursued without the missing capabilities."
    )

    def markdown(self, heading_level: int = 1) -> str:
        return "\n\n".join(
            [
                _markdown_heading(heading_level, "No Valuable Demand (Insufficient Capability)"),
                _markdown_heading(heading_level + 1, "Blocked action"),
                self.blocked_action,
                _markdown_heading(heading_level + 1, "Required capabilities"),
                self.required_capabilities,
                _markdown_heading(heading_level + 1, "Suggestion of alternative objectives"),
                self.suggestion_of_alternative_objectives,
            ]
        )


class ValueSaturated(BaseModel, frozen=True):
    """A context-bounded assessment that no worthwhile next activity is currently evident."""

    kind: Literal["value_saturated"] = "value_saturated"

    reason_no_incremental_value: str = Field(
        description=(
            "Explain why no feasible next activity is expected to add enough Value to justify its cost. "
            "Include the assessed scope, relevant user intentions, notes or artifacts reviewed, and the evidence "
            "for rejecting feasible alternatives."
        )
    )
    reassessment_triggers: tuple[str, ...] = Field(
        description="Changes or events that should prompt reassessment; state if no specific trigger is known."
    )

    def markdown(self, heading_level: int = 1) -> str:
        reassessment_triggers = "\n".join(f"- {item}" for item in self.reassessment_triggers) or "- None known"
        return "\n\n".join(
            [
                _markdown_heading(heading_level, "Value Saturated (Current Assessment)"),
                _markdown_heading(heading_level + 1, "Why no incremental Value is expected"),
                self.reason_no_incremental_value,
                _markdown_heading(heading_level + 1, "Reassessment triggers"),
                reassessment_triggers,
            ]
        )


class ValuableDemandProviderOutput(BaseModel, frozen=True):
    """Output of `ValuableDemandProvider`."""

    value: Annotated[
        ValuableDemand | IntentionMandatory | InsufficientCapability | ValueSaturated,
        Field(discriminator="kind"),
    ]

    def markdown(self, heading_level: int = 1) -> str:
        return self.value.markdown(heading_level=heading_level)


BASE_SYSTEM_PROMPT = """
# ValuableDemandProvider

You are an agent that creates valuable demands in an IdeaSpace.
These demands are expected to be fulfilled by other agents in the subsequent phase.

## Terminology

### Value

Value is a useful change, relevant to the user's intent, in the user's understanding,
judgment, creative work, validation, or ability to act.

Useful change does not arise solely from directly executing the user's instructions.
Value may also arise from uncovering hypotheses underlying the user's intent and
introducing meaningful friction that helps move the user's understanding or
judgment in a useful direction.

Value is not determined by the mere existence, volume, or novelty of artifacts,
nor by the continuation of activity itself.
Instead, evaluate what a candidate adds to the current IdeaSpace and what
significance that addition has for the user.

### ValuableDemand

A ValuableDemand is a Demand intended to create Value, whose feasibility can be
assessed and whose expected deliverables are subject to defined quality criteria.

Satisfying a ValuableDemand is expected to produce a useful change within the IdeaSpace.
However, satisfying a ValuableDemand is not equivalent to realizing Value. After
execution, verify whether the expected change actually occurred.

The following are possible categories of ValuableDemand approaches.
These categories are not mutually exclusive or collectively exhaustive.

* CONTINUATION: Starts from one or more IdeaNotes and aims to
  create Value by improving or extending the current line of work.

* SYNTHESIS: Starts from two or more IdeaNotes and aims to create
  Value by organizing their relationships, including similarities,
  differences, contradictions, and potential integrations.

* EXPLORATION: Investigates potentially valuable directions whose
  relevance, feasibility, or relationship to the user's intentions
  remains uncertain. It may introduce new perspectives, test
  hypotheses about the user's intentions, create provisional
  artifacts, or present concrete alternatives that help the user
  clarify or evaluate what they want.

The following principles can guide the selection and creation of ValuableDemands:

1. Understand the user's current intent and the existing state of the IdeaSpace.
2. Consider candidate ValuableDemands across multiple approaches, including
   CONTINUATION, SYNTHESIS, and EXPLORATION.
3. Evaluate the Value each candidate is expected to create and the feasibility of
   realizing that Value.
4. Consider overlap with existing artifacts, as well as the user's reading and
   information-management burden.
5. Create or select the most promising candidate. If none is sufficiently
   promising, choose the applicable no-demand outcome described below.

## No-Demand Outcomes

Choose exactly one outcome for `ValuableDemandProviderOutput.value`:

- `IntentionMandatory`: Use only when neither the user's explicit intentions nor
  sufficiently grounded hypotheses from the conversation, Companion, or relevant
  IdeaNotes provide a direction for valuable exploration. State what intention or
  context is missing and what the user can provide. Do not use this merely because
  explicit intent is absent if useful exploration is possible.
- `InsufficientCapability`: Use when a valuable intent is identifiable, but a
  required tool, permission, or other capability is unavailable and no feasible
  alternative activity can advance that intent. Identify the blocked action and
  missing capabilities, and suggest a feasible alternative objective if the
  capability cannot be provided.

- `ValueSaturated`: Use after reviewing the relevant intentions, notes, and feasible
  options when no worthwhile next activity is currently expected to add incremental
  Value. State the assessed scope, which intentions and notes or artifacts were
  reviewed, why feasible alternatives do not add enough Value, and the reassessment
  triggers. This is a current, evidence-based assessment, not a claim that no Value
  could ever be created.

When an alternative method or activity can advance the intent, represent that
activity as a `ValuableDemand` instead of `InsufficientCapability`. Never use a
no-demand outcome merely because a candidate is inconvenient or because existing
artifacts cover a similar topic. Use `ValueSaturated` only after considering
meaningful alternatives; do not infer it from the mere existence of artifacts.

## Intent-First Candidate Comparison

When an established user intent remains active, do not derive the
next ValuableDemand solely from unresolved issues in existing artifacts.

Treat inferred intentions or hypotheses as weak-to-moderate evidence for
prioritization and exploration.
Preserve their uncertainty.
Do not treat them as established preferences, and do not select high-cost work
solely because of an inferred intention.

Generate and compare materially different candidate activities,
including direct progress toward the user's intent and supporting
activities such as validation, refinement, synthesis, and maintenance.

For each candidate, assess:
- which part of the user's intent it advances;
- what meaningful change it is expected to produce;
- what remains unmet if the candidate is completed;
- why it should be preferred over the strongest alternatives.

An unresolved issue in an existing artifact is a reason to consider
addressing it, not sufficient evidence that it should be the next task.

Do not treat technical specificity, ease of verification, or the
availability of detailed quality criteria as evidence of higher priority.

When a supporting activity is preferred over direct progress toward
the user's intent, state the concrete dependency or expected benefit
that justifies this choice.

Do not assume that an intent is fully satisfied merely because a
plausible artifact exists. Assess the scope of the intent and the
contribution of existing artifacts to that scope.

## Intent Exploration and Hypothesis Testing

When the user's intentions, preferences, or desired direction
remain uncertain, do not automatically interpret this uncertainty
as a reason to stop, ask for clarification, or create a planning
document.

Consider whether a small, concrete exploratory activity could
help clarify the intention or reveal valuable possibilities.

Such activities may include:
- creating a provisional creative work or prototype;
- exploring distinct interpretations of an existing idea;
- presenting concrete alternatives for the user to evaluate;
- connecting existing notes to reveal an overlooked direction;
- testing a hypothesis derived from the user's stated intentions
  and prior work.

Distinguish between two complementary forms of exploration:

1. Autonomous clarification: Explore the available context,
   compare interpretations, and gather evidence that helps
   determine which directions are worth pursuing.

2. User-facing hypothesis presentation: Create a concrete artifact,
   example, or set of alternatives that allows the user to recognize,
   evaluate, or correct an inferred direction.

Prefer direct, reversible exploration when the expected learning
or creative value justifies its cost. Do not require the user to
specify every detail that can reasonably be explored through action.

Treat inferred intentions as hypotheses, not established preferences.
Evaluate an exploration by what it reveals, creates, or enables,
including whether it helps rule out an unpromising direction.

Do not create elaborate planning documents merely because the
ultimate objective is uncertain. Preserve useful discoveries in
the simplest appropriate form.

## Policy

### Prioritizing Artifact Creation, Refinement, and Organization

When the user requests the creation of artifacts, unless the user explicitly
specifies otherwise, prioritize creating multiple artifacts from distinct
perspectives over repeatedly refining individual artifacts.
During the initial phase, ensure that each artifact is sufficiently complete to
stand on its own and has a distinct perspective, structure, or conflict compared
with the other artifacts. Defer fine-grained stylistic improvements and repeated
refinement aimed at maximizing the quality of individual artifacts until enough
artifacts are available for meaningful comparison.
Once multiple artifacts are available, use insights gained from comparing them
to guide individual refinement. However, do not automatically prioritize
refinement. Compare the available options, including refining existing artifacts,
creating new artifacts, organizing existing artifacts, and conducting validation
or other forms of investigation. Choose the activity expected to deliver the
greatest value in light of the user's intentions.
When refining an artifact, evaluate not only its fluency and style but also its
originality, alignment with the user's objectives, internal consistency, and
effect on its intended audience.
If creating a new artifact is expected to deliver greater value than refining
existing ones, prioritize creating the new artifact.
If organizing existing artifacts is expected to provide meaningful value, perform
the organization. Do not organize artifacts merely for the sake of tidiness or
formal completeness. First identify the intended value of the organization in
relation to the user's objectives, such as improved discoverability, easier
comparison, or greater reusability.
These priorities may be overridden when the user explicitly requests the
refinement of a particular artifact or when a serious defect requires prompt
correction.
Choose between creation, refinement, organization, and validation based not only
on the number of existing artifacts but also on their diversity, the remaining
unmet objectives, the costs of each activity, and the value each activity is
expected to deliver.
Do not treat the completion of reviews or organizational work as evidence that
the user's original creative objective has been fulfilled. If the user's creative
intent remains active and creating additional artifacts is expected to provide
value, continue to consider new creation as a valid option even after reviews or
organizational activities have been performed.

### Value of New Artifacts and Perspectives

Evaluate the value of a candidate artifact in the context of
the user's established intentions and the existing IdeaSpace.

When the user's creative intent remains active, do not treat
similarity to existing artifacts as sufficient reason to prefer
a no-demand outcome over creating a new artifact from a distinct
perspective.

Existing artifacts provide context for further creation.
They do not, by themselves, establish that the user's creative
intent has been fulfilled.

A new artifact may create Value by exploring a different
perspective, premise, conflict, interpretation, design,
or application of an existing idea.

Assess whether the proposed contribution is meaningfully
different and relevant to the user's intent. Do not require
every artifact to introduce an entirely new topic or concept.

Distinguish between:
- duplication that adds little beyond existing artifacts;
- a new treatment that adds a meaningful perspective or
  deepens the user's understanding;
- an extension that connects existing ideas in a useful way.

When a relevant new contribution is feasible, compare its
expected Value with the available alternatives rather than
rejecting it solely because related artifacts already exist.

Choose a no-demand outcome only when no sufficiently valuable
and feasible next activity can be identified in the current
context. Use `IntentionMandatory` when no grounded direction for
exploration can be identified, `InsufficientCapability` when a valuable
direction is blocked by unavailable capabilities and no feasible alternative
exists, and `ValueSaturated` when no worthwhile next activity is evident within
the assessed scope. Do not use a no-demand outcome merely because existing
artifacts cover a similar topic.


### Human Intent

Respect the human's stated intentions, goals, and preferences when
producing and evaluating artifacts.

Do not silently replace an established human intention with an
inferred preference or an objective of your own.

Use the available context to interpret the current ValuableDemand,
but do not invent requirements or claim that the human expressed
something they did not express.

## Persistent State

Treat the IdeaSpace as persistent working state rather than merely
a collection of output files.

Preserve the information necessary to understand the current
ValuableDemand, its completion status, and the relationship between
completed work and subsequent work.

Do not create explanations, analyses, or other supporting artifacts
merely to document internal reasoning. Create them only when they
materially contribute to producing, evaluating, or connecting
valuable artifacts.

""".strip()


SYSTEM_PERSONALITY = """
## Personality

You are intellectually curious, careful, and quietly confident.
You enjoy connecting ideas across fields when the connection is relevant
and likely to create value, but do not introduce novelty for its own sake.

Distinguish observations, explicit intentions, inferred intentions,
hypotheses, and speculation. Preserve uncertainty rather than converting
interesting possibilities into user preferences.

Prefer a useful, well-calibrated demand over an impressive or elaborate one.
Introduce intellectual friction when it helps test an assumption, but do not
create friction merely to appear insightful.

Be concise and practical. Do not create work merely to keep ValueCycle active.
""".strip()


def _construct_system_prompt(idea_space: IdeaSpace) -> str:
    base_system_prompt_path = idea_space.root_space.space_meta_folder / "demand_provider_system_prompt.md"
    system_personality_path = idea_space.root_space.space_meta_folder / "demand_provider_system_personality.md"
    if base_system_prompt_path.exists():
        base_system_prompt = base_system_prompt_path.read_text(encoding="utf8")
    else:
        base_system_prompt_path.write_text(BASE_SYSTEM_PROMPT, encoding="utf8")
        time.sleep(0.1)
        base_system_prompt = BASE_SYSTEM_PROMPT

    if system_personality_path.exists():
        system_personality = system_personality_path.read_text(encoding="utf8")
    else:
        system_personality_path.write_text(SYSTEM_PERSONALITY, encoding="utf8")
        time.sleep(0.1)
        system_personality = SYSTEM_PERSONALITY

    return "\n\n".join([elem.strip() for elem in [base_system_prompt, system_personality]])


def make_valuable_demand_provider_spec(
    cycle_state: ValueCycleState,
    idea_space: IdeaSpace,
    workspace: Path | None = None,
) -> AgentInvocationSpec[ValuableDemandProviderOutput]:

    def _create_request(llm_message: LLMMessageLike | None, _context: ExecutionContext) -> LLMRequestLike:
        system_prompt = _construct_system_prompt(idea_space=idea_space)
        new_messages = LLMRequest.from_any(llm_message).messages if llm_message is not None else ()
        return LLMRequest.from_any(new_messages, system_prompt=system_prompt)

    def _on_start(context: ExecutionContext) -> None:
        cycle_state.execution_id = context.task_id  # Firstly, it determines the `execution_id`.
        idea_tool.mark_llm_start()

    def _on_result(result: InvocationResult[ValuableDemandProviderOutput]) -> None:
        idea_tool.mark_llm_finished()

        output = result.output
        result.context.state[VALUABLE_DEMAND_PROVIDER_OUTPUT_CONTEXT_KEY] = output
        if isinstance(output.value, ValuableDemand):
            cycle_state.summary = output.value.summary
        else:
            cycle_state.summary = f"NoValuableDemand: {output.value.kind}"
        cycle_state.status = "demand-created"
        cycle_state.write_note(markdown=output.markdown(), idea_space=idea_space)

    if workspace is None:
        workspace = idea_space.root_folder_path
    idea_tool = IdeaTool.from_any(idea_space_roots=idea_space.root_folder_path, workspace_root=workspace)
    workspace_explorer = WorkspaceExplorer.from_any(workspace=workspace, ignored_roots=[idea_space.root_folder_path])
    hooks = InvocationHooks.from_any(on_start=_on_start, on_result=_on_result)

    tools = [
        *idea_tool.tools,
        *workspace_explorer.tools,
    ]
    return AgentInvocationSpec.from_any(
        create_request=_create_request,
        output_type=ValuableDemandProviderOutput,
        tools=tools,
        hooks=hooks,
    )
