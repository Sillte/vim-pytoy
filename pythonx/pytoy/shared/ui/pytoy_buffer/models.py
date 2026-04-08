from pathlib import Path
from typing import Hashable, Literal, Self, Sequence
from pytoy.shared.lib.event.domain import Event


from dataclasses import dataclass

type BufferID = Hashable

@dataclass
class BufferEvents:
    on_wiped: Event[BufferID]
    on_pre_buf: Event[BufferID]
    
@dataclass(frozen=True)
class URI:  
    """Represents what the buffer represent.  
    """
    scheme: str
    path: str = ""  # Some `scheme` may not have the path.
    authority: str | None = None # Typically, `authority` is None.


@dataclass(frozen=True)
class BufferSource:
    """Source of buffer.
    """
    type: Literal["file", "nofile"]
    name: str

    @classmethod
    def from_path(cls, path: Path) -> Self:
        return cls(type="file", name=path.absolute().as_posix())

    @classmethod
    def from_no_file(cls, name: str) -> Self:
        return cls(type="nofile", name=name)

    @classmethod
    def from_str(cls, name: str, type: Literal["file", "nofile"] | None = None) -> Self:
        if not type:
            if name.find(".") == -1 and name.find("/") == -1 and name.find("\\") == -1:
                type = "nofile"
            else:
                type = "file"
        return cls(type=type, name=name)

    @classmethod
    def from_any(cls, arg: Path | str | Self) -> Self:

        if isinstance(arg, Path):
            return cls.from_path(arg)
        elif isinstance(arg, str):
            return cls.from_str(arg)
        elif isinstance(arg, cls):
             return arg
        raise ValueError("Type is invalid in `BufferSource`")


@dataclass(frozen=True)
class BufferQuery:
    """Source of buffer.
    """
    buffer_sources: Sequence[BufferSource] | None = None
    is_normal_type: bool = True
    
    @classmethod
    def from_source(cls, source: BufferSource, is_normal_type: bool = True) -> Self:
        return cls(buffer_sources=[source], is_normal_type=is_normal_type)
