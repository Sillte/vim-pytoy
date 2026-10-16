from pathlib import Path

from pytoy_llm.idea import IdeaSpace
from pytoy_llm.task.models import TaskSpec

from .convention import CONVENTION
from .demand_fulfiller_invocation import make_demand_fulfiller_spec
from .demand_provider_invocation import make_value_demand_provide_spec
from .value_auditor_invocation import make_value_auditor_spec

MASTER_FOLDER_NAME = "master"
INITIAL_USER_INTENT = """
# Initial User Intent

No explicit user intent has been recorded yet.

When proposing valuable work, consider relevant existing materials
in the IdeaSpace and the available workspace.
If you find potentially valuable proposals, create `ValuableDemand`. 
Otherwise, `NoValuableDemand` should be passed.
""".strip()


def make_task_spec(idea_space: IdeaSpace, workspace: Path | None) -> TaskSpec:
    prepare_idea_space(idea_space)
    invocations = [
        make_value_demand_provide_spec(idea_space, workspace=workspace),
        make_demand_fulfiller_spec(idea_space, workspace=workspace),
        make_value_auditor_spec(idea_space, workspace=workspace),
    ]
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
