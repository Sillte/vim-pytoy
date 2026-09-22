from typing import Sequence, assert_never

from pytoy.shared.lib.text import (
    CharacterRange,
    LineRange,
    NoReplacePatch,
    ReplaceCharactersPatch,
    ReplaceLinesPatch,
    ReplacePatch,
)
from pytoy.shared.ui.contract.buffer import RangeOperatorProtocol


class RangeOperator(RangeOperatorProtocol):
    """Return the `str` related to Buffer."""

    def __init__(self, impl: RangeOperatorProtocol):
        self._impl = impl

    def get_lines(self, line_range: LineRange) -> list[str]:
        return self._impl.get_lines(line_range)

    def get_text(self, character_range: CharacterRange) -> str:
        return self._impl.get_text(character_range)

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange:
        return self._impl.replace_lines(line_range, lines)

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        return self._impl.replace_text(character_range, text)

    def find_first(
        self,
        text: str,
        target_range: CharacterRange | None = None,
        reverse: bool = False,
    ) -> CharacterRange | None:
        """return the first mached selection of `text`."""
        return self._impl.find_first(text, target_range, reverse=reverse)

    def find_all(self, text: str, target_range: CharacterRange | None = None) -> list[CharacterRange]:
        """return the all matched selections of `text`"""
        return self._impl.find_all(text, target_range)

    @property
    def entire_character_range(self) -> CharacterRange:
        return self._impl.entire_character_range

    def apply_patch(self, replace_patch: ReplacePatch) -> ReplacePatch:
        """Apply a replacement patch to the buffer.

        Returns:
            A replacement patch that restores the buffer to its previous state.
            Applying the returned patch once restores the buffer before this
            operation.
        """
        match replace_patch:
            case NoReplacePatch():
                return NoReplacePatch()
            case ReplaceLinesPatch():
                old_lines = self._impl.get_lines(replace_patch.line_range)
                new_character_range = self._impl.replace_lines(replace_patch.line_range, replace_patch.lines)
                return ReplaceLinesPatch(line_range=new_character_range, lines=old_lines)
            case ReplaceCharactersPatch():
                old_text = self._impl.get_text(replace_patch.character_range)
                new_character_range = self._impl.replace_text(replace_patch.character_range, replace_patch.text)
                return ReplaceCharactersPatch(character_range=new_character_range, text=old_text)
            case _:
                assert_never(replace_patch)
