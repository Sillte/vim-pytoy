from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Self

from pytoy.shared.lib.text import CursorPosition


@dataclass
class QuickfixRecord:
    filename: str
    lnum: int
    col: int = 1
    text: str = ""
    valid: bool = True
    end_lnum: int | None = None
    end_col: int | None = None
    vcol: bool = False
    type: str | None = None
    nr: int | None = None
    pattern: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "filename": self.filename,
            "lnum": self.lnum,
            "col": self.col,
            "text": self.text,
        }
        if self.vcol:
            data["vcol"] = 1
        if self.type is not None:
            data["type"] = self.type
        if self.nr is not None:
            data["nr"] = self.nr
        if self.pattern is not None:
            data["pattern"] = self.pattern
        if not self.valid:
            data["valid"] = 0
        if self.end_lnum is not None:
            data["end_lnum"] = self.end_lnum
        if self.end_col is not None:
            data["end_col"] = self.end_col
        return data

    @classmethod
    def _to_filename(cls, raw_filename: str, cwd: Path | None) -> str:
        path_obj = Path(raw_filename)
        if not path_obj.is_absolute():
            if cwd is None:
                raise ValueError(f"{cwd} is not given, but relative path is given.")
            return str(cwd / path_obj)
        return str(path_obj)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], cwd: Path | str) -> Self:
        if isinstance(cwd, str):
            cwd = Path(cwd)
        return cls(
            filename=cls._to_filename(data["filename"], cwd),
            lnum=int(data.get("lnum", 1)),
            col=int(data.get("col", 1)),
            text=data.get("text", ""),
            vcol=bool(data.get("vcol", 0)),
            type=data.get("type"),
            nr=data.get("nr"),
            pattern=data.get("pattern"),
            valid=bool(data.get("valid", 1)),
            end_lnum=data.get("end_lnum"),
            end_col=data.get("end_col"),
        )

    @property
    def cursor(self) -> CursorPosition:
        return CursorPosition(self.lnum - 1, self.col - 1)


@dataclass
class QuickfixState:
    index: int | None
    size: int

    def __post_init__(self):
        if self.size < 0:
            raise ValueError("QuickfixState: size must not be negative. ")
        if self.size == 0:
            self.index = None
        elif self.index is None:
            self.index = 0
        elif self.index:
            self.index %= self.size
