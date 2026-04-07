from __future__ import annotations
from enum import StrEnum
from typing import Literal, Self, TYPE_CHECKING, assert_never
from dataclasses import dataclass
from pytoy.shared.lib.text import CursorPosition, CharacterRange, LineRange

if TYPE_CHECKING:
    from pytoy.shared.ui.pytoy_window.protocol import PytoyWindowProtocol

class ViewportMoveMode(StrEnum):
    """When Cursor/Selection is changed,
    this specifies how the viewport of the window changes.
    """
    NONE = "none"
    ENSURE_VISIBLE = "ensure_visibile"
    CENTER = "center"
    TOP = "top"

@dataclass(frozen=True)
class ViewPort():
    top_line: int  # The start number.  (0 starts.)
    left_col: int # The left column number (0 starts.)
    end_line: int  # The end line number, exclusive.  
    right: int # The right column number (exclusive).
    # If necessary, in the fugure.
    ...
    @property
    def line_range(self) -> LineRange:
        return LineRange(self.top_line, self.end_line)



@dataclass
class WindowCreationParam:
    """Configuration for creating PytoyWindow. 
    """
    try_reuse: bool = True
    target : Literal["in-place", "split"] = "split"
    anchor: PytoyWindowProtocol | None = None
    split_direction: Literal["vertical", "horizontal", None] = "vertical"
    cursor: CursorPosition | None = None

    def __post_init__(self):
        if self.target == "split":
            assert self.split_direction in {"vertical", "horizontal"}
        else:
            assert self.split_direction is None

    @classmethod 
    def for_split(cls,
                  split_direction: Literal["vertical", "horizontal"],
                  try_reuse: bool = False, 
                  anchor: PytoyWindowProtocol | None = None,
                  cursor: CursorPosition | None = None) -> Self:
        return cls(try_reuse=try_reuse,
                   target="split",
                   split_direction=split_direction,
                   anchor=anchor,
                   cursor=cursor)

    @classmethod 
    def for_in_place(cls,
                     try_reuse: bool = False,
                     anchor: PytoyWindowProtocol | None = None,
                     cursor: CursorPosition | None = None) -> Self:
        return cls(try_reuse=try_reuse,
                   target="in-place",
                   split_direction=None,
                   anchor=anchor,
                   cursor=cursor)

    @classmethod
    def from_literal(cls, arg: Literal["vertical", "horizontal", "in-place"]) -> Self:
        """Make shift generation when the simple creation is necessary.
        """
        default_try_reuse = False
        match arg:
            case "vertical":
                return cls.for_split(arg, try_reuse=default_try_reuse)
            case "horizontal":
                return cls.for_split(arg, try_reuse=default_try_reuse)
            case "in-place":
                return cls.for_in_place(try_reuse=default_try_reuse)
            case _:
                assert_never(arg)


