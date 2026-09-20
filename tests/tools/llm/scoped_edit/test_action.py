import pytest

from pytoy.shared.lib.text import CharacterRange, CursorPosition
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer
from pytoy.shared.ui.pytoy_window import PytoyWindow
from pytoy.tools.llm.scoped_edit.action import ScopedEditAction


class FailingTaskMaker:
    def make_task(self, document, contract):
        raise ValueError("expected failure")


def test_execute_reverts_markers_when_task_creation_fails() -> None:
    window = PytoyWindow.open(BufferSource.from_no_file("scoped-edit-sync-failure"))
    buffer = PytoyBuffer(window.buffer)
    buffer.init_buffer("original")
    character_range = CharacterRange(CursorPosition(0, 0), CursorPosition(0, 8))
    action = ScopedEditAction(FailingTaskMaker(), buffer, character_range)

    with pytest.raises(ValueError, match="expected failure"):
        action.execute()

    assert "original" in buffer.content
    assert action.scoped_edit_contract.query_start not in buffer.content
    assert action.scoped_edit_contract.query_end not in buffer.content


@pytest.mark.parametrize(
    "output",
    [
        "[pytoy-llm][test]>$>\nchanged",
        "changed\n>$>[pytoy-llm][test]",
        ">$>[pytoy-llm][test]\n[pytoy-llm][test]>$>\nchanged",
    ],
)
def test_apply_output_reverts_markers_when_output_marker_pair_is_invalid(output: str) -> None:
    window = PytoyWindow.open(BufferSource.from_no_file("scoped-edit-invalid-output"))
    buffer = PytoyBuffer(window.buffer)
    buffer.init_buffer("original")
    character_range = CharacterRange(CursorPosition(0, 0), CursorPosition(0, 8))
    action = ScopedEditAction(FailingTaskMaker(), buffer, character_range)
    action.scoped_edit_contract = action.scoped_edit_contract.from_id("test")
    action.scoped_edit_contract.insert_markers(buffer, character_range)

    action._apply_output(buffer, output)

    assert "original" in buffer.content
    assert action.scoped_edit_contract.query_start not in buffer.content
    assert action.scoped_edit_contract.query_end not in buffer.content


def test_apply_output_extracts_content_from_a_valid_marker_pair() -> None:
    window = PytoyWindow.open(BufferSource.from_no_file("scoped-edit-valid-output"))
    buffer = PytoyBuffer(window.buffer)
    buffer.init_buffer("original")
    character_range = CharacterRange(CursorPosition(0, 0), CursorPosition(0, 8))
    action = ScopedEditAction(FailingTaskMaker(), buffer, character_range)
    action.scoped_edit_contract = action.scoped_edit_contract.from_id("test")
    action.scoped_edit_contract.insert_markers(buffer, character_range)

    action._apply_output(buffer, "[pytoy-llm][test]>$>\nchanged\n>$>[pytoy-llm][test]")

    assert buffer.content == "changed"
