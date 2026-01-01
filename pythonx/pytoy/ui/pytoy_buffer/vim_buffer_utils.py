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

    def replace_lines(self, line_range: LineRange, lines: Sequence[str]) -> LineRange:
        line1, line2 = line_range.start, line_range.end
        line2 = max(line2, len(self.buffer))
        self.buffer[line1:line2] = lines
        return LineRange(line1, line2)


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
            elif len(lines) == 1:
                return lines[0][start.col: end.col]
            else:
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
            # NOTE: Vim buffer lines are newline-terminated
            if end.line == len(vim_buffer):
                return "\n".join(lines)
            else:
                return "\n".join(lines) + "\n"

        vim_buffer = self.buffer
        if character_range.end.col == 0:
            return _zero_end_col(vim_buffer, character_range)
        elif 0 < character_range.end.col:
            return _positive_end_col(vim_buffer, character_range)
        else:
            msg = "ImplementaionError of `VimBufferRangeSelector`"
            raise AssertionError(msg)

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        def _positive_end_col(
            vim_buffer: "vim.Buffer", character_range: CharacterRange, text: str
        ) -> CharacterRange:
            target_lines = text.split("\n")
            n_target_lines = len(target_lines)
            start, end = character_range.start, character_range.end
            # Related lines.
            lines = vim_buffer[start.line : end.line + 1]
            n_lines = len(lines)

            if n_target_lines == 1:
                end_l = start.line
                end_c = start.col + len(target_lines[-1])
                cr = CharacterRange(start, CursorPosition(end_l, end_c))
                if n_lines == 1:
                    target_line = target_lines[0]
                    new_line = lines[0][: start.col] + target_line + lines[0][end.col: ]
                    vim_buffer[start.line : end.line + 1] = [new_line]
                else:
                    target_lines[0] = lines[0][: start.col] + target_lines[0] + lines[-1][end.col :]
                    vim_buffer[start.line : end.line + 1] = target_lines
                return cr
            else:
                end_l = start.line + n_target_lines - 1
                end_c = len(target_lines[-1])
                cr = CharacterRange(start, CursorPosition(end_l, end_c))

                target_lines[0] = lines[0][: start.col] + target_lines[0]
                target_lines[-1] = target_lines[-1] + lines[-1][end.col :]
                vim_buffer[start.line : end.line + 1] = target_lines
                return cr


        def _zero_end_col(
            vim_buffer: "vim.Buffer", character_range: CharacterRange, text: str
        ) -> CharacterRange:
            start, end = character_range.start, character_range.end
            assert end.col == 0
            target_lines = text.split("\n") # It assueres that `target_lines` is not empty.
            n_target_lines = len(target_lines)
            assert target_lines
            lines = vim_buffer[start.line : end.line]  # `end` line is not included.
            n_lines = len(lines)
            if len(target_lines) == 1:
                end_l = start.line + n_target_lines - 1
                end_c = start.col + len(target_lines[-1])
                cr = CharacterRange(start, CursorPosition(end_l, end_c))

                if n_lines == 0:
                    assert start.col == 0 and end.col == 0, (start, end)
                    vim_buffer[start.line : end.line] = target_lines
                else:
                    target_lines[0] = lines[0][:start.col] + target_lines[0]
                    vim_buffer[start.line : end.line] = target_lines
                return cr
            else:
                end_l = start.line + n_target_lines - 1
                end_c = len(target_lines[-1])
                cr = CharacterRange(start, CursorPosition(end_l, end_c))
                if n_lines == 0:
                    assert start.col == 0 and end.col == 0
                    vim_buffer[start.line : end.line] = target_lines
                else:
                    target_lines[0] = lines[0][:start.col] + target_lines[0]
                    vim_buffer[start.line : end.line] = target_lines
                return cr


        vim_buffer = self.buffer
        if character_range.end.col == 0:
            return _zero_end_col(vim_buffer, character_range, text)
        elif 0 < character_range.end.col:
            return _positive_end_col(vim_buffer, character_range, text)
        else:
            msg = "ImplementaionError of `VimBufferRangeSelector`"
            raise AssertionError(msg)
