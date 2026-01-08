from pytoy.infra.core.models import CursorPosition
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol
from pytoy.ui import get_ui_enum, UIEnum
from pytoy.infra.core.models import CharacterRange, LineRange
from typing import Sequence


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

