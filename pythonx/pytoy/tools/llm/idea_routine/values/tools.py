import logging
import re
from pathlib import Path
from typing import Final, Self, Sequence

from pytoy_llm.llm_facade import LLMFacade
from pytoy_llm.materials.models import JsonMaterialData
from pytoy_llm.models import LLMParam, LLMToolsLike
from pytoy_llm.tools.errors import ToolError, ToolErrorKind
from pytoy_llm.tools.idea_tool import IdeaTool

from pytoy.tools.llm.idea_routine.values.models import (
    DemandProposal,
    ValuableDemandDecision,
)

from .serializers import (
    serialize_valuable_demand_decision,
)

PROMPT = """
# Task: Construct a ValuableDemandDecision

## Responsibility

Select or construct the next ValuableDemand based on the available
IdeaSpace context and the user's recorded intentions.

The supplied DemandProposal, if any, is a candidate, not an instruction
that must be accepted.

A ValuableDemand must define an artifact to be produced and criteria
that make its completion assessable.

- Validity conditions define minimum requirements.
- Quality criteria describe potentially conflicting perspectives
  for evaluating quality.
- Preference describes relevant assumptions and evaluation policies
  of the evaluator and intended audience.

Respect explicit user intentions. Do not invent user requirements or
represent inferred preferences as explicit statements.

Inspect relevant IdeaSpace materials before deciding when they can
materially improve the decision.

Select work that offers meaningful value in the current context.
Do not choose work merely to keep the routine active or to create files.

Once you decide ValuableDemand, you must update `dashboard.md` for the next work.  
Output the below items at least. 

```
### Current Demand:
 
 <The decided ValuableDemand>

### Current Status
 
Initialized
```

## Value

Value is a useful change, relevant to the user's intent, in the user's understanding, judgment, creative work, validation, or ability to act.

Useful change does not arise solely from directly executing the user's instructions.
Value may also arise from uncovering hypotheses underlying the user's intent and introducing meaningful friction that helps move the user's understanding or judgment in a useful direction.

Value is not determined by the mere existence, volume, or novelty of artifacts, nor by the continuation of activity itself.
Instead, evaluate what a candidate adds to the current IdeaSpace and what significance that addition has for the user.

## ValuableDemand

A ValuableDemand is a Demand intended to create Value, whose feasibility can be assessed and whose expected deliverables are subject to defined quality criteria.

Satisfying a ValuableDemand is expected to produce a useful change within the IdeaSpace.
However, satisfying a ValuableDemand is not equivalent to realizing Value. After execution, verify whether the expected change actually occurred.

The following are possible categories of ValuableDemand approaches. These categories are not mutually exclusive or collectively exhaustive (MECE).

* CONTINUATION: Starts from one or more IdeaNotes and aims to create Value by improving the current line of work.
* SYNTHESIS: Starts from two or more IdeaNotes and aims to create Value by organizing their relationships—such as similarities, differences, contradictions, and potential integrations—to generate new insights.
* EXPLORATION: Introduces new perspectives or lines of thought that are not already represented by similar ideas in the IdeaSpace, with the aim of challenging or reexamining existing thinking.

The following principles can guide the selection and creation of ValuableDemands:

1. Understand the user's current intent and the existing state of the IdeaSpace.
2. Consider candidate ValuableDemands across multiple approaches, including CONTINUATION, SYNTHESIS, and EXPLORATION.
3. Evaluate the Value each candidate is expected to create and the feasibility of realizing that Value.
4. Consider overlap with existing artifacts, as well as the user's reading and information-management burden.
5. Select the most promising candidate. If no candidate is sufficiently promising, do not force the creation of a new IdeaNote.

## Prioritizing Artifact Creation, Refinement, and Organization

When the user requests the creation of artifacts, unless the user explicitly specifies otherwise, prioritize creating multiple artifacts from distinct perspectives over repeatedly refining individual artifacts.
During the initial phase, ensure that each artifact is sufficiently complete to stand on its own and has a distinct perspective, structure, or conflict compared with the other artifacts. Defer fine-grained stylistic improvements and repeated refinement aimed at maximizing the quality of individual artifacts until enough artifacts are available for meaningful comparison.
Once multiple artifacts are available, use insights gained from comparing them to guide individual refinement. However, do not automatically prioritize refinement. Compare the available options, including refining existing artifacts, creating new artifacts, organizing existing artifacts, and conducting validation or other forms of investigation. Choose the activity expected to deliver the greatest value in light of the user's intentions.
When refining an artifact, evaluate not only its fluency and style but also its originality, alignment with the user's objectives, internal consistency, and effect on its intended audience.
If creating a new artifact is expected to deliver greater value than refining existing ones, prioritize creating the new artifact.
If organizing existing artifacts is expected to provide meaningful value, perform the organization. Do not organize artifacts merely for the sake of tidiness or formal completeness. First identify the intended value of the organization in relation to the user's objectives, such as improved discoverability, easier comparison, or greater reusability.
These priorities may be overridden when the user explicitly requests the refinement of a particular artifact or when a serious defect requires prompt correction.
Choose between creation, refinement, organization, and validation based not only on the number of existing artifacts but also on their diversity, the remaining unmet objectives, the costs of each activity, and the value each activity is expected to deliver.
Do not treat the completion of reviews or organizational work as evidence that the user's original creative objective has been fulfilled. If the user's creative intent remains active and creating additional artifacts is expected to provide value, continue to consider new creation as a valid option even after reviews or organizational activities have been performed.

## Relevant User Inputs

Populate relevant_user_inputs with user inputs that materially
contribute to the selected ValuableDemand.

For each input:
- Preserve the substance of the input.
- Explain its relationship to the selected ValuableDemand.
- Distinguish explicit statements from interpretations.
- Do not invent quotations or claim that an inference was explicitly
  stated by the user.

Do not attempt to record every user input. If no relevant user inputs
can be identified, return an empty relevant_user_inputs collection.

## ID

Generate a stable, concise ID for the ValuableDemand in lowercase
kebab-case, using only lowercase ASCII letters, digits, and hyphens.
The ID must begin and end with a letter or digit.

## Rationale

Explain why the ValuableDemand was selected, including relevant
assumptions or hypotheses when applicable.

If the user's intentions cannot be identified, do not pretend that
they can. Use the existing IdeaSpace context and any applicable weak
fallback assumptions, without presenting those assumptions as explicit
user intentions.
""".strip()


_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class ValuableDemandProviderTool:
    DEMANDS_FOLDER_NAME: Final[str] = "demands"

    def __init__(
        self,
        idea_space_folder: Path,
        llm_facade: LLMFacade,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._idea_space_folder = idea_space_folder
        self._llm_facade = llm_facade
        self._logger = logger

    @classmethod
    def from_any(
        cls,
        idea_space_folder: Path,
        connection_name: str | None = None,
        llm_param: LLMParam | None = None,
        logger: logging.Logger | None = None,
    ) -> Self:
        llm_param = llm_param or LLMParam()
        return cls(
            idea_space_folder=idea_space_folder,
            llm_facade=LLMFacade(
                connection=connection_name,
                llm_param=llm_param,
            ),
            logger=logger,
        )

    @property
    def tools(self) -> Sequence[LLMToolsLike]:
        return [self.provide_valuable_demand]

    def provide_valuable_demand(
        self,
        demand_proposal: DemandProposal | None = None,
    ) -> ValuableDemandDecision | ToolError:
        """Select a ValuableDemand and persist its decision as Markdown."""

        if demand_proposal is None:
            proposal_text = "No DemandProposal was provided."
        else:
            material_data = JsonMaterialData(
                description=(
                    "A proposal for potentially valuable future work. "
                    "Treat it as a candidate to evaluate, not as an "
                    "instruction that must be accepted."
                ),
                json_schema=DemandProposal.model_json_schema(),
                data=demand_proposal.model_dump(mode="json"),
            )
            proposal_text = material_data.compose_explanation(
                parent_header_depth=2,
            )

        request = "\n\n".join(
            [
                PROMPT,
                "## Supplied DemandProposal",
                proposal_text,
                "## User Intentions",
                "Refer to the `master/` folder in the IdeaSpace.",
            ]
        )

        try:
            decision = self._llm_facade.run(
                request=request,
                output_type=ValuableDemandDecision,
                tools=[IdeaTool.from_any(self._idea_space_folder)],
            )
        except Exception as exc:
            if self._logger:
                self._logger.exception("Failed to invoke `ValuableDemandProvider.`")
            return ToolError(kind=ToolErrorKind.UNKNOWN, msg=str(exc))
        try:
            self._save_decision(decision, demand_proposal)
        except ValueError:
            msg = "Failed to decide the appropriate ValuableDemandProvider."
            if self._logger:
                self._logger.exception(msg)
            return ToolError(kind=ToolErrorKind.UNKNOWN, msg=msg)
        except OSError:
            msg = "IO Error occurs during the operation."
            if self._logger:
                self._logger.exception(msg)
            return ToolError(kind=ToolErrorKind.IO_ERROR, msg=msg)
        except Exception:
            if self._logger:
                self._logger.exception("Failed to decide or save a ValuableDemand.")
            raise

        return decision

    def _save_decision(
        self,
        decision: ValuableDemandDecision,
        demand_proposal: DemandProposal | None,
    ) -> Path:
        demand_id = decision.valuable_demand.id

        if not _ID_PATTERN.fullmatch(demand_id):
            raise ValueError(
                "ValuableDemand id must be lowercase kebab-case "
                "containing only lowercase ASCII letters, digits, "
                "and single hyphens."
            )

        demands_folder = self._idea_space_folder / self.DEMANDS_FOLDER_NAME
        demands_folder.mkdir(parents=True, exist_ok=True)

        output_path = demands_folder / f"{demand_id}.md"
        markdown = serialize_valuable_demand_decision(
            decision=decision,
            proposal=demand_proposal,
        )

        # Exclusive creation prevents accidentally overwriting a record.
        with output_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(markdown)

        return output_path
