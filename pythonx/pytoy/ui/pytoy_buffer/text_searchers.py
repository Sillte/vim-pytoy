from pytoy.infra.core.models import CursorPosition, CharacterRange
from typing import Sequence, Self


class TextSearcher:
    """Find the target `text` from the lines.
    Note that `col_offset` is meaningful only when the first line is the target.
    """
    def __init__(self, lines: Sequence[str], line_offset:  int, col_offset: int):
        self.lines = lines
        self._content, self._line_offsets = self._build_text_and_offsets(lines)
        self.line_offset = line_offset
        self.col_offset = col_offset


    @classmethod
    def create(cls,
                      lines: Sequence[str],
                      target_range: CharacterRange | None = None,
                      ) -> Self:
        """
        Create a TextSearcher whose internal text is restricted to the given range.

        - The search is performed only within the sliced text.
        - Returned CharacterRange is always mapped back to the original coordinates.

        `line_offset` is propagated the final CharacterRange. 
        In all the lines, it assumes that `lines` starts from `line_offset`.
        """

        if target_range is None:
            return cls(lines=lines, line_offset=0, col_offset=0)
        if not lines:
            return cls(lines=lines, line_offset=0, col_offset=0)
        start, end = target_range.start, target_range.end

        if start.line == end.line:
            target_line = lines[start.line]
            return cls(lines=[target_line[start.col:end.col]], line_offset=start.line, col_offset=start.col)
        else:
            first_line = lines[start.line][start.col:]
            final_line = lines[end.line][: target_range.end.col]
            target = [first_line,  *lines[start.line + 1: end.line], final_line]
            return cls(lines=target, line_offset=start.line, col_offset=start.col)

    def _build_text_and_offsets(self, lines: Sequence[str]) -> tuple[str, list[int]]:
        """Return the concatenated text and offsets of lines."""
        text = "\n".join(lines)
        offsets = []
        pos = 0
        for line in lines:
            offsets.append(pos)
            pos += len(line) + 1  # +1 for '\n'
        return text, offsets

    def _cursor_to_index(self, pos: CursorPosition) -> int:
        return self._line_offsets[pos.line] + pos.col

    def _index_to_cursor(self, index: int) -> CursorPosition:
        # find rightmost line whose offset <= index
        line = 0
        for i, offset in enumerate(self._line_offsets):
            if offset > index:
                break
            line = i
        col = index - self._line_offsets[line]
        return CursorPosition(line=line, col=col)
 

    def find_first(
        self,
        text: str,
        reverse: bool = False,
    ) -> CharacterRange | None:
        if not text:
            return None

        if reverse:
            idx = self._content.rfind(text)
        else:
            idx = self._content.find(text)

        if idx == -1:
            return None

        start_cursor = self._index_to_cursor(idx)
        end_cursor = self._index_to_cursor(idx + len(text))
        return self._solve_offset(start_cursor, end_cursor)

    def find_all(self, text: str) -> list[CharacterRange]:
        """return the all matched selections of `text`"""
        if not text:
            return []
        results: list[CharacterRange] = []
        start = 0
        while True:
            idx = self._content.find(text, start)
            if idx == -1:
                break
            s = self._index_to_cursor(idx)
            e = self._index_to_cursor(idx + len(text))
            results.append(self._solve_offset(s, e))
            start = idx + len(text)
        return results

    def _solve_offset(self, start_cursor: CursorPosition, end_cursor: CursorPosition) -> CharacterRange:

        def _solve(cursor: CursorPosition) -> CursorPosition:
            line = cursor.line + self.line_offset
            if cursor.line == 0:
                col = cursor.col + self.col_offset
            else:
                col = cursor.col
            return CursorPosition(line, col)
        start = _solve(start_cursor)
        end = _solve(end_cursor)
        return CharacterRange(start=start, end=end)
