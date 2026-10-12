from .models import DemandProposal, ValuableDemandDecision


def serialize_valuable_demand_decision(
    decision: ValuableDemandDecision,
    proposal: DemandProposal | None = None,
) -> str:
    """Serialize a ValuableDemand decision and its optional proposal."""

    demand = decision.valuable_demand

    if not demand.id.strip():
        raise ValueError("ValuableDemand id must not be empty.")

    if proposal is None:
        proposal_sections = [
            "\n## Proposal",
            "\nNo proposal was provided.",
        ]
    else:
        proposal_sections = [
            "\n## Proposal",
            "\n### Objective",
            proposal.objective.strip(),
            "\n### Rationale",
            proposal.rationale.strip(),
        ]

    sections = [
        f"# ValuableDemand: {demand.id}",
        "\n## Decision",
        "\n### Validity Conditions",
        demand.validity_conditions.strip(),
        "\n### Quality Criteria",
        demand.quality_criteria.strip(),
        "\n### Preference",
        (demand.preference.strip() if demand.preference is not None else "Not specified."),
        *proposal_sections,
        "\n## Relevant User Input",
    ]

    if decision.relevant_user_inputs:
        for index, user_input in enumerate(
            decision.relevant_user_inputs,
            start=1,
        ):
            input_lines = user_input.input.strip().splitlines()
            quoted_input = "\n".join(f"> {line}" if line else ">" for line in input_lines)

            sections.extend(
                [
                    f"\n### Input {index}",
                    quoted_input,
                    "\n#### Relationship to the ValuableDemand",
                    user_input.relationship.strip(),
                ]
            )
    else:
        sections.append("\nNo relevant user inputs are recorded for this decision.")

    sections.extend(
        [
            "\n## Decision Rationale",
            decision.rationale.strip(),
        ]
    )

    return "\n\n".join(sections).strip() + "\n"
