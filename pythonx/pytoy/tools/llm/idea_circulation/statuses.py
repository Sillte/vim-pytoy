from dataclasses import dataclass, field
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field
from pytoy_llm.models import LLMTokens


def _empty_llm_tokens() -> LLMTokens:
    return LLMTokens(prompt=0, completion=0, total=0, cache_read=0, cache_write=0)


type ValueCycleExecutionPolicy = Annotated[
    Literal["enabled", "paused"],
    Field(
        description="In case of `enabled`, `ValueCycle` is invoked periodically. In case of `paused`, invocation is skipped.  "
    ),
]


@dataclass
class IdeaCirculationStatus:
    kind: ClassVar[str] = "idea-circulation"
    workspace_name: str | None
    value_cycle_working_status: str | None
    value_cycle_execution_policy: ValueCycleExecutionPolicy = field(default="enabled")
    value_cycle_message: str | None = None
    llm_tokens: LLMTokens = field(default_factory=_empty_llm_tokens)

    def update_tokens(self, llm_tokens: LLMTokens) -> None:
        self.llm_tokens = LLMTokens.aggregate([self.llm_tokens, llm_tokens])

    def change_value_cycle_execution_policy(self, execution_policy: ValueCycleExecutionPolicy) -> None:
        self.value_cycle_execution_policy = execution_policy

    def change_value_cycle_message(self, message: str) -> None:
        self.value_cycle_message = message


class IdeaCirculationStatusPatch(BaseModel, frozen=True):
    """Update of the status of `IdeaCirculation`.
    This class controls the execution policy of autonomous activities
    such as `ValueCycle` (`ValuableDemandProvider`)
    """

    value_cycle_execution_policy: ValueCycleExecutionPolicy | None = Field(
        default=None,
        description="If the literal other than `null` specified, change the status of `ValueCycleExecutionPolicy`.",
    )

    reason: str | None = Field(
        default=None,
        description="Very concice explanation for the change of policies. In case that no changes are requiest, `null` is appropriate.",
    )

    def apply(self, status: IdeaCirculationStatus) -> None:
        if self.value_cycle_execution_policy is not None:
            status.value_cycle_execution_policy = self.value_cycle_execution_policy
