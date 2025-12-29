from pytoy.infra.core.models import CursorPosition, LineRange
import vim
from pytoy.infra.core.models import CharacterRange
from typing import Sequence


class VimBufferRangeHandler:
    def __init__(self, buffer: "vim.Buffer | int"):
        if isinstance(buffer, int):
            buffer = vim.buffers[buffer]
        self._buffer = buffer

    @property
    def buffer(self) -> "vim.Buffer":
        return self._buffer

    def get_lines(self, line_range: LineRange) -> list[str]:
        """Note that line1 and line2 is 0-based.
        The end is exclusive.
        """
        line1, line2 = line_range.start, line_range.end
        return self.buffer[line1:line2]

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> None:
        line1, line2 = line_range.start, line_range.end
        self.buffer[line1:line2] = lines

    def get_text(self, character_range: CharacterRange) -> str:
        """`line` and `pos` are number acquried by `getpos`."""

        # Note that `start.line` and `end.line` is 0-based.
        # Note that `start.col` and `end.col` is 0-based.
        # Note that `end` of character_range is exclusive.
        def _positive_end_col(vim_buffer: "vim.Buffer", character_range: CharacterRange):
            start, end = character_range.start, character_range.end
            lines = vim_buffer[start.line : end.line + 1]
            if not lines:
                return ""
            lines[0] = lines[0][start.col :]
            lines[-1] = lines[-1][: end.col]
            return "\n".join(lines)

        def _zero_end_col(vim_buffer: "vim.Buffer", character_range: CharacterRange):
            start, end = character_range.start, character_range.end
            assert end.col == 0
            lines = vim_buffer[start.line : end.line]  # `end` line is not included.
            if not lines:
                return ""
            lines[0] = lines[0][start.col :]
            return "\n".join(lines) + "\n"

        vim_buffer = self.buffer
        if character_range.end.col == 0:
            return _zero_end_col(vim_buffer, character_range)
        elif 0 < character_range.end.col:
            return _positive_end_col(vim_buffer, character_range)
        else:
            msg = "ImplementaionError of `VimBufferRangeSelector`"
            raise RuntimeError(msg)

    def replace_text(self, character_range: CharacterRange, text: str) -> None:
        def _positive_end_col(
            vim_buffer: "vim.Buffer", character_range: CharacterRange, text: str
        ) -> None:
            target_lines = text.split("\n")
            start, end = character_range.start, character_range.end
            # Related lines.
            lines = vim_buffer[start.line : end.line + 1]
            target_lines[0] = lines[0][: start.col] + target_lines[0]
            target_lines[-1] = target_lines[-1] + lines[-1][end.col :]
            vim_buffer[start.line : end.line + 1] = target_lines

        def _zero_end_col(
            vim_buffer: "vim.Buffer", character_range: CharacterRange, text: str
        ) -> None:
            start, end = character_range.start, character_range.end
            assert end.col == 0
            target_lines = text.split("\n")
            lines = vim_buffer[start.line : end.line]  # `end` line is not included.
            if lines:
                target_lines[0] = lines[0][: start.col] + target_lines[0]
                vim_buffer[start.line : end.line] = target_lines
            else:
                # e.g start.line == end.line, (3, 0), (3, 0)  
                vim_buffer[end.line: end.line] = target_lines

        vim_buffer = self.buffer
        if character_range.end.col == 0:
            return _zero_end_col(vim_buffer, character_range, text)
        elif 0 < character_range.end.col:
            return _positive_end_col(vim_buffer, character_range, text)
        else:
            msg = "ImplementaionError of `VimBufferRangeSelector`"
            raise RuntimeError(msg)
