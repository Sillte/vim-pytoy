from pathlib import Path

from pytoy.shared.command import App
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer

app = App()


@app.command("IdeaRecent")
def idea_recent():
    from pytoy_llm.idea import IdeaSpace

    from pytoy.shared.ui.pytoy_quickfix import (
        Quickfix,
        QuickfixRecord,
    )

    def get_rececnt_idea_notes(idea_space: IdeaSpace):
        notes = idea_space.get_notes(depth=None)
        return sorted(notes, key=lambda note: Path(note.file_path).stat().st_mtime, reverse=True)

    current_buffer = PytoyBuffer.get_current()
    if current_buffer.is_file:
        file_path = current_buffer.file_path
        idea_space = IdeaSpace.from_path(file_path)
    else:
        idea_space = current_buffer.metadata.data.get("idea-space")
        if idea_space is None:
            raise ValueError()
    notes = get_rececnt_idea_notes(idea_space)
    records = [QuickfixRecord(filename=note.file_path.as_posix(), lnum=1) for note in notes]
    quick_fix = Quickfix.from_any(records, kind="idea-space-quickfix", try_reuse=True)
    quick_fix.provide_ui("pytoy").show()
