from __future__ import annotations
from enum import StrEnum
from pathlib import Path 
from typing import Literal, Self, TYPE_CHECKING, assert_never
from dataclasses import dataclass

if TYPE_CHECKING:
    from pytoy.ui.pytoy_window.protocol import PytoyWindowProtocol

class ViewportMoveMode(StrEnum):
    """When Cursor/Selection is changed,
    this specifies how the viewport of the window changes.
    """
    NONE = "none"
    ENSURE_VISIBLE = "ensure_visibile"
    CENTER = "center"
    TOP = "top"
    

@dataclass
class BufferSource:
    """Source of buffer.
    """
    type: Literal["file", "nofile"]
    name: str
    
    @classmethod
    def from_path(cls, path: Path) -> Self:
        return cls(type="file", name=path.absolute().as_posix())

    @classmethod
    def from_str(cls, name: str, type: Literal["file", "nofile"] | None = None) -> Self:
        if not type: 
            if name.find(".") == -1 and name.find("/") == -1 and name.find("\\") == -1:
                type = "nofile"
            else:
                type = "file"
        return cls(type=type, name=name)

    @classmethod
    def from_any(cls, arg: Path | str) -> Self:

        if isinstance(arg, Path):
            return cls.from_path(arg)
        elif isinstance(arg, str):
            return cls.from_str(arg)
        raise ValueError("Type is invalid in `BufferSource`")


@dataclass
class WindowCreationParam:
    """Configuration for creating PytoyWindow. 
    """
    try_reuse: bool = True
    target : Literal["in-place", "split"] = "split"
    anchor: PytoyWindowProtocol | None = None
    split_direction: Literal["vertical", "horizontal", None] = "vertical"

    def __post_init__(self):
        if self.target == "split":
            assert self.split_direction in {"vertical", "horizontal"}
        else:
            assert self.split_direction is None

    @classmethod 
    def for_split(cls,
                  split_direction: Literal["vertical", "horizontal"],
                  try_reuse: bool = False, 
                  anchor: PytoyWindowProtocol | None = None) -> Self:
        return cls(try_reuse=try_reuse,
                   target="split",
                   split_direction=split_direction,
                   anchor=anchor)

    @classmethod 
    def for_in_place(cls,
                     try_reuse: bool = False,
                     anchor: PytoyWindowProtocol | None = None) -> Self:
        return cls(try_reuse=try_reuse,
                   target="in-place",
                   split_direction=None,
                   anchor=anchor)
        
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


