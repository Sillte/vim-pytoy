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
        line2 = min(line2, len(self.buffer))
        self.buffer[line1:line2] = lines
        return LineRange(line1, line1 + len(lines))


    def get_text(self, character_range: CharacterRange) -> str:
        """`line` and `pos` are number acquried by `getpos`."""

        # Note that `start.line` and `end.line` is 0-based.
        # Note that `start.col` and `end.col` is 0-based.
        # Note that `end` of character_range is exclusive.
        def _resolve_cols(lines: list[str],
                          firstline_start_col: int | None = None,
                          lastline_end_col: int | None = None) -> None:
            """start_col is inclusive, end_col is exclusive.
            """
            if not lines:
                return
            if len(lines) == 1:
                lines[0] = lines[0][firstline_start_col: lastline_end_col]
            else:
                lines[0] = lines[0][firstline_start_col:]
                lines[-1] = lines[-1][: lastline_end_col]

        vim_buffer = self.buffer
        start, end = character_range.start, character_range.end
        if character_range.end.col == 0:
            lines = vim_buffer[start.line : end.line]  # `end` line is not included.
            if not lines:
                return ""
            _resolve_cols(lines, firstline_start_col=start.col, lastline_end_col=None)
            last_lf = "\n" if end.line < len(vim_buffer) else ""
            return "\n".join(lines) + last_lf
        elif 0 < character_range.end.col:
            lines = vim_buffer[start.line : end.line + 1]
            if not lines:
                return ""
            _resolve_cols(lines, firstline_start_col=start.col, lastline_end_col=end.col)
            return "\n".join(lines)
        else:
            msg = "ImplementaionError of `VimBufferRangeSelector`"
            raise AssertionError(msg)

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        def _calc_replaced_range(
            start: CursorPosition,
            inserted_lines: list[str],
        ) -> CharacterRange:
            assert inserted_lines, "ImplementaionError."
            end_l = start.line + len(inserted_lines) - 1
            if len(inserted_lines) == 1:
                end_c = start.col + len(inserted_lines[0])
            else:
                end_c = len(inserted_lines[-1])
            return CharacterRange(start, CursorPosition(end_l, end_c))

        def _resolve_surrounding(insert_lines: list[str], 
                                 firstline_prefix: str | None = None,
                                 lastline_suffix:  str | None = None) -> None:
            assert insert_lines
            firstline_prefix = firstline_prefix or ""
            lastline_suffix = lastline_suffix or ""
            if len(insert_lines) == 1:
                insert_lines[0] = firstline_prefix + insert_lines[0] + lastline_suffix
            else:
                insert_lines[0] = firstline_prefix + insert_lines[0]
                insert_lines[-1] = insert_lines[-1] + lastline_suffix

        vim_buffer = self.buffer

        start, end = character_range.start, character_range.end
        target_lines = text.split("\n") # It assueres that `target_lines` is not empty.
        assert target_lines
        cr = _calc_replaced_range(start, target_lines)
        if character_range.end.col == 0:
            lines = vim_buffer[start.line : end.line]
            firstline_prefix = lines[0][:start.col] if lines else None
            lastline_suffix = None
            _resolve_surrounding(target_lines, firstline_prefix, lastline_suffix)
            vim_buffer[start.line : end.line] = target_lines
        else:
            lines = vim_buffer[start.line : end.line + 1]
            firstline_prefix = lines[0][: start.col]
            lastline_suffix = lines[-1][end.col: ]
            _resolve_surrounding(target_lines, firstline_prefix, lastline_suffix)
            vim_buffer[start.line : end.line + 1] = target_lines
        return cr