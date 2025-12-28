from dataclasses import dataclass
from typing import Self

@dataclass(frozen=True)
class CursorPosition:
    """This represents the position of cursor.
    Here, both of `line` and `col` are 0-based.
    Note that `line` and `col` in vim start from 1, while 
    thoese start from 0 in vscode.
    Hence, you have to take it into account to implement
    the concrete classs for vim/vscode.
    """
    line: int  # 0-based.
    col: int  # 0-based.


@dataclass
class Selection:
    """This represents the selection of the range.
    `end` is inclusive. 
    """
    start: CursorPosition
    end: CursorPosition

    def __post_init__(self):
        items = (self.start, self.end)
        self.start, self.end = sorted(items, key=lambda elem: (elem.line, elem.col))

    @classmethod
    def from_numbers(cls, line1: int, col1: int, line2: int, col2: int) -> Self:
        return cls(start=CursorPosition(line1, col1), end=CursorPosition(line2, col2))
