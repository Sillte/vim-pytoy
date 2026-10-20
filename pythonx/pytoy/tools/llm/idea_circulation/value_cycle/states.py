from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pytoy_llm.idea import IdeaNote, IdeaSpace

type ValueCycleStatus = Literal["started", "demand-created", "artifacts-created", "finished"]

VALUABLE_DEMAND_PROVIDER_OUTPUT_CONTEXT_KEY = "value_cycle.valuable_demand_provider_output"
FULFILLMENT_REPORT_CONTEXT_KEY = "value_cycle.fulfillment_report"
VALUE_AUDIT_CONTEXT_KEY = "value_cycle.value_audit"


@dataclass
class ValueCycleState:
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    status: ValueCycleStatus = field(default="started")
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = field(default=None)
    summary: str | None = field(default=None)
    value_cycle_log_folder_name: str = field(default="value_cycle_log")

    def write_note(self, markdown: str, idea_space: IdeaSpace):
        folder = idea_space.root_directory_path / self.value_cycle_log_folder_name
        folder.mkdir(exist_ok=True, parents=True)
        path = folder / f"{self.execution_id}.md"
        idea_note = IdeaNote.create(path, body=markdown)
        idea_note.metadata["id"] = self.execution_id
        idea_note.metadata["status"] = self.status
        idea_note.metadata["started_at"] = self.started_at.isoformat()
        if self.finished_at is not None:
            idea_note.metadata["finished_at"] = self.finished_at.isoformat()
        if self.summary:
            idea_note.metadata["summary"] = self.summary
        idea_note.write()
