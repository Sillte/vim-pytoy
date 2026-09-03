from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Self, assert_never

from pytoy.shared.lib.text import CursorPosition, LineRange

if TYPE_CHECKING:
    from pytoy.shared.ui.contract.window import WindowProtocol


class ViewportMoveMode(StrEnum):
    NONE = "none"
    ENSURE_VISIBLE = "ensure_visibile"
    CENTER = "center"
    TOP = "top"


@dataclass(frozen=True)
class ViewPort:
    top_line: int
    left_col: int
    end_line: int
    right: int

    @property
    def line_range(self) -> LineRange:
        return LineRange(self.top_line, self.end_line)


@dataclass
class WindowCreationParam:
    try_reuse: bool = True
    target: Literal["in-place", "split"] = "split"
    anchor: WindowProtocol | None = None
    split_direction: Literal["vertical", "horizontal", None] = None
    cursor: CursorPosition | None = None

    def __post_init__(self):
        if self.target == "split":
            self.split_direction = self.split_direction or "vertical"

    @classmethod
    def for_split(
        cls,
        split_direction: Literal["vertical", "horizontal"],
        try_reuse: bool = False,
        anchor: WindowProtocol | None = None,
        cursor: CursorPosition | None = None,
    ) -> Self:
        return cls(try_reuse=try_reuse, target="split", split_direction=split_direction, anchor=anchor, cursor=cursor)

    @classmethod
    def for_in_place(
        cls, try_reuse: bool = False, anchor: WindowProtocol | None = None, cursor: CursorPosition | None = None
    ) -> Self:
        return cls(try_reuse=try_reuse, target="in-place", split_direction=None, anchor=anchor, cursor=cursor)

    @classmethod
    def from_literal(cls, arg: Literal["vertical", "horizontal", "in-place"]) -> Self:
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
