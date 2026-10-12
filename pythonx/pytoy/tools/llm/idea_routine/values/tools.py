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

## Continuation Judgment

When a DemandProposal substantially overlaps with recent work or
existing artifacts, do not accept it merely because it follows
naturally from the current ValuableDemand.

Evaluate the proposal in terms of:

- Feasibility: Is there a credible way to complete the work with
  the available capabilities and resources?
- Incremental value: What meaningful value would this work add
  beyond existing artifacts and previous attempts?
- Expected impact: Is that additional value important enough to
  justify continuing the same line of work?

Reject or redirect proposals that repeat known-impossible actions
or offer only marginal improvements without a clear justification.

Allow continued work when it addresses an important unresolved
issue, introduces meaningful new evidence or insight, or
substantially improves an existing artifact.

When continuation is not sufficiently justified, consider a
different user intention, topic, perspective, or use of existing
artifacts.

Do not assume that overlap alone makes a proposal redundant.
Base the decision on the actual state of prior work, the
remaining gap, and the value of closing that gap.

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
