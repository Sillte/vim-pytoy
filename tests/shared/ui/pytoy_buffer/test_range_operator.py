from pytoy.shared.lib.text import (
    CharacterRange,
    CursorPosition,
    LineRange,
    ReplaceCharactersPatch,
    ReplaceLinesPatch,
)
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer.range_operator import RangeOperator


def test_range_operator_reads_lines_and_text() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer("zero\none\ntwo")
    operator = buffer.range_operator

    assert isinstance(operator, RangeOperator)
    assert operator is buffer.range_operator
    assert operator.get_lines(LineRange(1, 3)) == ["one", "two"]
    assert operator.get_text(CharacterRange(CursorPosition(0, 1), CursorPosition(1, 2))) == "ero\non"


def test_range_operator_replaces_lines() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer("zero\none\ntwo")

    result = buffer.range_operator.replace_lines(LineRange(1, 3), ["ONE", "TWO"])

    assert result == LineRange(1, 3)
    assert buffer.lines == ["zero", "ONE", "TWO"]


def test_range_operator_replaces_text() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer("zero\none\ntwo")

    result = buffer.range_operator.replace_text(
        CharacterRange(CursorPosition(0, 1), CursorPosition(1, 2)),
        "X",
    )

    assert result == CharacterRange(CursorPosition(0, 1), CursorPosition(0, 2))
    assert buffer.content == "zXe\ntwo"


def test_range_operator_applies_line_patch_and_returns_inverse_patch() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer("zero\none\ntwo")

    inverse_patch = buffer.range_operator.apply_patch(ReplaceLinesPatch(LineRange(1, 3), ["ONE"]))

    assert buffer.lines == ["zero", "ONE"]
    assert inverse_patch == ReplaceLinesPatch(LineRange(1, 2), ["one", "two"])

    buffer.range_operator.apply_patch(inverse_patch)

    assert buffer.content == "zero\none\ntwo"


def test_range_operator_applies_character_patch_and_returns_inverse_patch() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer("zero\none\ntwo")
    character_range = CharacterRange(CursorPosition(0, 1), CursorPosition(1, 2))

    inverse_patch = buffer.range_operator.apply_patch(ReplaceCharactersPatch(character_range, "X"))

    assert buffer.content == "zXe\ntwo"
    assert inverse_patch == ReplaceCharactersPatch(
        CharacterRange(CursorPosition(0, 1), CursorPosition(0, 2)),
        "ero\non",
    )


def test_range_operator_finds_matches() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer("one two\none two")
    operator = buffer.range_operator

    assert operator.find_first("two") == CharacterRange(CursorPosition(0, 4), CursorPosition(0, 7))
    assert operator.find_first("two", reverse=True) == CharacterRange(CursorPosition(1, 4), CursorPosition(1, 7))
    assert operator.find_all("two") == [
        CharacterRange(CursorPosition(0, 4), CursorPosition(0, 7)),
        CharacterRange(CursorPosition(1, 4), CursorPosition(1, 7)),
    ]
