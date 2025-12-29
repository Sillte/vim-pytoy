from pytoy.infra.core.models import CursorPosition
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol
from pytoy.ui import get_ui_enum, UIEnum
from pytoy.infra.core.models import CharacterRange, LineRange
from typing import Sequence


class RangeOperator(RangeOperatorProtocol):
    """Return the `str` related to Buffer."""

    def __init__(self, impl: RangeOperatorProtocol):
        self._impl = impl

    @property
    def buffer(self) -> PytoyBufferProtocol:
        return self._impl.buffer

    def get_lines(self, line_range: LineRange) -> list[str]:
        return self._impl.get_lines(line_range)

    def get_text(self, character_range: CharacterRange) -> str:
        return self._impl.get_text(character_range)

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> None:
        return self._impl.replace_lines(line_range, lines)

    def replace_text(self, character_range: CharacterRange, text: str) -> None:
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


def make_range_operator(impl_buffer: PytoyBufferProtocol) -> RangeOperator:
    if get_ui_enum() == UIEnum.VSCODE:
        from pytoy.ui.pytoy_buffer.impl_vscode import (
            RangeOperatorVSCode,
            PytoyBufferVSCode,
        )

        assert isinstance(impl_buffer, PytoyBufferVSCode)
        impl = RangeOperatorVSCode(impl_buffer)
        return RangeOperator(impl)
    else:
        from pytoy.ui.pytoy_buffer.impl_vim import RangeOperatorVim, PytoyBufferVim

        assert isinstance(impl_buffer, PytoyBufferVim)
        impl = RangeOperatorVim(impl_buffer)
        return RangeOperator(impl)
