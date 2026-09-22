from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CursorPosition:
    """A zero-based position in a text document.

    Both ``line`` and ``col`` are zero-based. ``col`` is measured in
    Python string indices, i.e. Unicode code points rather than bytes.

    This position is independent of any editor-specific coordinate system.
    Concrete integrations such as Vim or VS Code must convert their native
    positions to and from this representation.
    (c.f. line and col are 1-based in vim while they are 0-based in vscode.)
    """

    line: int  # 0-based.
    col: int  # 0-based, Unicode codepoint index (Python str index)


@dataclass(frozen=True)
class CharacterRange:
    """A half-open range of text positions. [start, end).

    ``start`` is inclusive and ``end`` is exclusive.

    Positions are expressed using :class:`CursorPosition`.
    If ``end`` precedes ``start``, the positions are normalized so that
    ``start <= end``.

    An empty range is represented by ``start == end`` and can be used as
    an insertion point.
    """

    start: CursorPosition
    end: CursorPosition

    def __post_init__(self):
        if (self.end.line, self.end.col) < (self.start.line, self.start.col):
            start, end = self.end, self.start
            object.__setattr__(self, "start", start)
            object.__setattr__(self, "end", end)

    @property
    def is_empty(self) -> bool:
        return self.start == self.end

    def as_line_range(self, cut_first_line: bool = False, cut_last_line: bool = False) -> "LineRange":
        if cut_first_line and self.start.col != 0:
            start = self.start.line + 1
        else:
            start = self.start.line

        if self.end.col == 0:
            end = self.end.line
        elif cut_last_line:
            end = self.end.line
        else:
            end = self.end.line + 1
        return LineRange(start, max(start, end))


@dataclass(frozen=True)
class LineRange:
    """A zero-based half-open range of lines. `[start, end)`

    ``start`` is inclusive and ``end`` is exclusive.

    Examples:
        ``LineRange(0, 1)`` selects line 0.
        ``LineRange(0, 0)`` is an empty range at the beginning of line 0.
    """

    start: int
    end: int

    @property
    def count(self) -> int:
        """Return the number of lines in the range."""
        return self.end - self.start


@dataclass(frozen=True)
class ReplaceLinesPatch:
    """Replace a contiguous range of lines with the given lines.

    The target range uses zero-based, half-open line coordinates.
    """

    line_range: LineRange
    lines: Sequence[str]


@dataclass(frozen=True)
class ReplaceCharactersPatch:
    """Replace a contiguous range of characters with the given text.

    The target range uses zero-based, half-open character coordinates.
    """

    character_range: CharacterRange
    text: str


@dataclass(frozen=True)
class NoReplacePatch:
    """Represents the absence of a text replacement.

    This is a successful result of an edit computation, not an error
    or a missing patch.
    """


type ReplacePatch = ReplaceLinesPatch | ReplaceCharactersPatch | NoReplacePatch
