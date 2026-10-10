from pydantic import BaseModel, Field


class ValuableDemand(BaseModel, frozen=True):
    """A set of criteria supplied by the external world for evaluating the value of an artifact."""

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


class DemandProposal(BaseModel, frozen=True):
    """A proposal for potentially valuable future work."""

    objective: str = Field(
        description=(
            "What should be accomplished by the proposed work. "
            "Describe the intended outcome rather than merely an activity."
        )
    )

    rationale: str = Field(
        description=("Why the proposed objective may create value, considering the available context.")
    )


class ValuableDemandDecision(BaseModel, frozen=True):
    """The result of selecting or constructing a ValuableDemand."""

    valuable_demand: ValuableDemand = Field(description="The selected or constructed ValuableDemand.")

    rationale: str = Field(
        description=(
            "Why this demand was selected or constructed, considering human intent, proposals, and IdeaSpace context."
        )
    )
