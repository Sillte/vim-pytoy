from pydantic import BaseModel, Field
from typing import Literal, Self
from typing_extensions import Annotated
from textwrap import dedent

CompassProgress = Annotated[
    Literal["emerging", "shaping", "committed"],
    Field(description=("Degree of maturity of the objective:\n"
                       "- emerging: not yet fixed\n"
                       "- shaping: partially clarified\n"
                       "- committed: fixed and prioritized\n")),
]


class Compass(BaseModel, frozen=True):
    """The objective of the document and confidence of the objective.

    Attributes:
        progress: Degree of how fixed or mature the objective is.
        objective: Description of the intended goal. Can be empty if not yet defined.
    """

    progress: CompassProgress
    objective: Annotated[
        str,
        Field(description="Objective of what we are creating. Can be empty initially."),
    ]

    @property
    def prompt_fragment(self) -> str:
        prompt = (
            f"Manuscript Objective: {self.objective or '(not yet defined)'}\n"
            f"Progress: {self.progress} (Refer to the schema of `Compass` for details.)\n"
        )
        return prompt



AlignmentState = Annotated[
    Literal["undefined", "inadequate", "acceptable", "excellent", "masterpiece"],
    Field(
        description=(
            "State of the document compared to the objective defined by Compass. "
            "`undefined` : Compass not yet set or objective not defined.\n"
            "`inadequate` : Document needs substantial improvement.\n"
            "`acceptable` : Document aligns with Compass, minor adjustments may be needed, however, it may not be satisfactory.\n"
            "`excellent` : Document fulfills its purpose, and it is satisfactory to some degree.\n"
            "`masterpiece`: Document is the supreme."
            "This state serves as guidance for Reflect (output evaluation) and Evolve (amount of revision)."
        )
    ),
]


class CompassAlignment(BaseModel, frozen=True):
    """
    Represents the alignment of the current document with the Compass.

    Attributes:
        state: AlignmentState indicating how well the document satisfies the objective.
        reason: Natural language explanation for why this state was assigned.
    """

    state: AlignmentState
    reason: Annotated[
        str, Field(description="The reason explaining the alignment state.")
    ]


class Bearing(BaseModel, frozen=True):
    """
    The current assessment of the document.

    Attributes:
        alignment: CompassAlignment showing current alignment with the document's objective.
        assessment: Free-text evaluation or commentary on the document's current state.
    """

    alignment: CompassAlignment
    assessment: Annotated[
        str, Field(description="Evaluation of the document's current state.")
    ]

    @property
    def bearing_description(self) -> str:
        """
        Generates a natural language description of the current bearing,
        suitable for inclusion in a system prompt for LLM.
        """
        return (
            f"Current alignment: {self.alignment.state}\n"
            f"Reason: {self.alignment.reason}\n"
            f"Assessment: {self.assessment}\n"
        )


class EvolvePolicy(BaseModel):
    """Policy of edit or generation of `manuscript`.

    When degree is "extreme", prioritize breaking creative stagnation
    over preserving local coherence.
    """
    degree: Annotated[
        Literal["auto", "low", "medium", "high", "extreme"],
        Field(
            description="""
    Growth pressure applied to the manuscript.

    - auto:
        Adjust pressure based on Compass progress and current maturity.

    - low:
        Gentle refinement. Preserve structure and voice.
        Stimulate subtle improvement.

    - medium:
        Strong refinement. Improve structure, sharpen themes,
        enhance emotional dynamics.

    - high:
        Intensive stimulation. Bold reinterpretation and structural
        reshaping are allowed while preserving the Compass objective.
    - extreme:
        Break stagnation mode.
        Apply radical restructuring or reinterpretation
        specifically to overcome creative deadlock.
        Introduce unexpected shifts in structure, perspective,
        or thematic emphasis if necessary.
        The Compass objective must still be satisfied.
    """
        )
    ] = "auto"

    comment: Annotated[str, 
                       Field(description="Comments for the current manuscript, revision. or critique.")] = "No specific comments. Apply the growth pressure autonomously."

