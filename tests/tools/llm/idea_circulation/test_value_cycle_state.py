from datetime import UTC, datetime
from pathlib import Path

from pytoy_llm.idea import IdeaNote, IdeaSpace

from pytoy.tools.llm.idea_circulation.value_cycle.states import ValueCycleState


def test_write_note_serializes_timestamps(tmp_path: Path) -> None:
    idea_space = IdeaSpace.from_path(tmp_path, root=tmp_path, with_creation=True)
    state = ValueCycleState(
        started_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 10, 20, 12, 5, tzinfo=UTC),
    )

    state.write_note("# Value cycle", idea_space)

    note_path = tmp_path / "value_cycle_log" / f"{state.execution_id}.md"
    note = IdeaNote.from_path(note_path, root=tmp_path)
    assert note.body == "# Value cycle"
    assert note.metadata["started_at"] == "2026-10-20T12:00:00+00:00"
    assert note.metadata["finished_at"] == "2026-10-20T12:05:00+00:00"
