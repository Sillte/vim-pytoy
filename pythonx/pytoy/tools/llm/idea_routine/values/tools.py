import logging
import random
from pathlib import Path
from typing import Self, Sequence

from pytoy_llm.llm_facade import LLMFacade
from pytoy_llm.materials.models import JsonMaterialData
from pytoy_llm.models import LLMParam, LLMToolsLike
from pytoy_llm.tools.idea_tool import IdeaTool

from pytoy.tools.llm.idea_routine.values.examples import (
    make_mathematical_proof_demand,
    make_python_article_demand,
    make_ss_demand,
)
from pytoy.tools.llm.idea_routine.values.models import DemandProposal, ValuableDemandDecision

PROMPT = """
# Task: Construct ValuableDemandDecision (ValuableDemandDecision and rationale)

## Rule

You are responsible for selecting or constructing the next ValuableDemand.

Consider the available IdeaSpace context, the users's recorded
intentions, and the supplied DemandProposal, if any.

The DemandProposal is a candidate, not an instruction that must
be accepted.

A ValuableDemand must define an artifact to be produced and
criteria that make its completion assessable.

Decide the following perspectives on the basis of user's intentions.
ValidityConditions define minimum requirements.
QualityCriteria describe potentially conflicting perspectives
for evaluating quality.
Preference describes relevant assumptions and evaluation policies
of the evaluator and intended audience.

Respect explicit user intentions. Do not invent user's requirements
or treat inferred preferences as explicit statements.

Inspect relevant IdeaSpace materials before deciding when they
can materially improve the decision.

Select or construct a ValuableDemand that offers meaningful value
in the current context. Do not choose work merely to keep the
routine active or to create more files.

Explain the decision in the rationale.

## User's intentions

`master/` space includes the intentions of the user.
Refer to `master/` folder.

If you cannot identify the user's intentions or preference of the user at all,
you are able to assume that the user has interests of the following topics.  

Use the listed interests only as weak fallback assumptions
when no actionable human intention can be identified from
`master/` or the existing IdeaSpace context.
Do not use these assumptions to override an explicit intention
or a meaningful ongoing line of work.
```markdown
* Domain Driven Design(DDD)
* Mathematical proof and its understandable explanation
* Seemingly pedantic, but practical knowledge of python
* 月刊少女野崎君
* Philosophy of Michael Sandel
* Nexus: A Brief History of Information Networks from the Stone Age to AI
```

""".strip()


class ValuableDemandProviderTool:
    def __init__(self, idea_space_folder: Path, llm_facade: LLMFacade, *, logger: logging.Logger | None = None) -> None:
        self._value_demands_examples = [
            make_ss_demand(),
            make_python_article_demand(),
            make_mathematical_proof_demand(),
        ]
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
            llm_facade=LLMFacade(connection=connection_name, llm_param=llm_param),
            logger=logger,
        )

    @property
    def tools(self) -> Sequence[LLMToolsLike]:
        return [self.provide_valuable_demand]

    def provide_valuable_demand(self, demand_proposal: DemandProposal | None = None) -> ValuableDemandDecision:
        """ValuableDemandProvider. It returns ValueableDemandDecision.

        Even if the tool functions fails, it returns the ValuableDemandDecision which does not reflect
        the user's intentions.

        Args:
            demand_proposal: DemandProposal or null:
                If meaning `demand_proposal` is impossible to make, set this argument as `null`.
        Return:
            ValuableDemandDecision
                The desicion of ValuableDemand.
                It is expected that this decision is described as the confirmed item.
        """

        def _make_prompt() -> str:
            if demand_proposal is not None:
                material_data = JsonMaterialData(
                    description=(
                        "A proposal for potentially valuable future work. "
                        "Treat it as a candidate to evaluate, not as an instruction "
                        "that must be accepted."
                    ),
                    json_schema=DemandProposal.model_json_schema(),
                    data=demand_proposal.model_dump(mode="json"),
                )
                proposal_text = material_data.compose_explanation(parent_header_depth=2)
            else:
                proposal_text = "No DemandProposal was suggested."
            return "\n\n".join([PROMPT, "## Supplied DemandProposal", proposal_text])

        def _random_selection() -> ValuableDemandDecision:
            demand = random.choice(self._value_demands_examples)
            return ValuableDemandDecision(
                valuable_demand=demand,
                rationale=(
                    "The LLM-based decision process failed. "
                    "A fallback ValuableDemand was selected randomly from "
                    "the predefined examples. This decision does not imply "
                    "that the selected demand matches the user's intentions."
                ),
            )

        try:
            decision = self._llm_facade.run(
                request=_make_prompt(),
                output_type=ValuableDemandDecision,
                tools=[IdeaTool.from_any(self._idea_space_folder)],
            )
        except Exception:
            decision = _random_selection()
            if self._logger:
                self._logger.exception("Decision of ValuableDemand fails.")
        return decision
