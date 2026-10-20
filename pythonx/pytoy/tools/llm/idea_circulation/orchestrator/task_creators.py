from pathlib import Path
from typing import Sequence

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.models import LLMMessage
from pytoy_llm.task.models import TaskSpec

from pytoy.tools.llm.idea_circulation.idea_exchange import IdeaExchangeResponse, make_idea_exchange_spec
from pytoy.tools.llm.idea_circulation.value_cycle.demand_fulfiller_invocation import make_demand_fulfiller_spec
from pytoy.tools.llm.idea_circulation.value_cycle.demand_provider_invocation import make_value_demand_provide_spec
from pytoy.tools.llm.idea_circulation.value_cycle.states import ValueCycleState
from pytoy.tools.llm.idea_circulation.value_cycle.value_auditor_invocation import (
    ValueAuditResponse,
    make_value_auditor_spec,
)

from .convention import CONVENTION

MASTER_FOLDER_NAME = "master"
INITIAL_USER_INTENT = """
# Initial User Intent

No explicit user intent has been recorded yet.

When proposing valuable work, consider relevant existing materials
in the IdeaSpace and the available workspace.
If you find potentially valuable proposals, create `ValuableDemand`. 
Otherwise, `NoValuableDemand` should be passed.
""".strip()


def create_value_cycle_task_spec(idea_space: IdeaSpace, workspace: Path | None) -> TaskSpec[ValueAuditResponse]:
    prepare_idea_space(idea_space)
    state = ValueCycleState()
    invocations = [
        make_value_demand_provide_spec(state, idea_space, workspace=workspace),
        make_demand_fulfiller_spec(state, idea_space, workspace=workspace),
        make_value_auditor_spec(state, idea_space, workspace=workspace),
    ]
    return TaskSpec.from_specs(invocation_specs=invocations)


def create_idea_exchange_task_spec(
    message_history: Sequence[LLMMessage], idea_space: IdeaSpace, workspace: Path | None
) -> TaskSpec[IdeaExchangeResponse]:
    prepare_idea_space(idea_space)
    invocations = [make_idea_exchange_spec(message_history, idea_space, workspace=workspace)]
    return TaskSpec.from_specs(invocation_specs=invocations)


def prepare_idea_space(idea_space: IdeaSpace):
    folder_path = idea_space.root_directory_path
    convention_path = folder_path / ".convention.md"
    master_folder_path = folder_path / MASTER_FOLDER_NAME
    if not folder_path.exists():
        folder_path.mkdir(exist_ok=True, parents=True)
    if not convention_path.exists():
        convention_path.write_text(CONVENTION, encoding="utf8")

    master_folder_path.mkdir(exist_ok=True, parents=True)

    initial_intent_path = master_folder_path / "intentions.md"
    if not initial_intent_path.exists():
        initial_intent_path.write_text(
            INITIAL_USER_INTENT,
            encoding="utf-8",
        )
