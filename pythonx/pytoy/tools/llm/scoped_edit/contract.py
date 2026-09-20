from dataclasses import dataclass
from typing import Protocol, Sequence

from pytoy_llm.task.models import TaskSpec


@dataclass(frozen=True)
class ScopedEditLLMContract:
    rules: Sequence[str]  # These rules form the contract with the LLM.
    override_rules: Sequence[str]  # Rules for handling user directives within the scoped edit.


class ScopedEditTaskMakerProtocol(Protocol):
    """Making a task for `ScopedEdit`.

    The implementater must insert `contract` to `SystemPrompt` .
    """

    def make_task(self, document: str, contract: ScopedEditLLMContract) -> TaskSpec: ...
