from dataclasses import dataclass
from typing import Any, Self, Mapping
from pathlib import Path
from pytoy.infra.core.models import CursorPosition

@dataclass
class QuickFixRecord:
    """Record of QuickFix.
    """
    # Required parameters
    filename: str  # This must be the absolute path
    lnum: int  # 1-based, from the defintion of `QuickFix in Vim`.
    col: int = 1 # 1-based, from the defintion of `QuickFix in Vim`.
    text: str = ""

    valid: bool = True
    end_lnum: int | None = None
    end_col: int | None = None

    # [TODO]: Basically, below is not used...
    # if not used, erase them...
    # optional parameters
    vcol: bool = False
    type: str | None = None     # "E", "W", "I", "N" など
    nr: int | None  = None       # エラー番号
    pattern: str | None = None  # 正規表現パターン



    def to_dict(self) -> dict[str, Any]:
        d = {
            "filename": self.filename,
            "lnum": self.lnum,
            "col": self.col,
            "text": self.text,
        }
        # Optional fields (only add if meaningful)
        if self.vcol:
            d["vcol"] = 1  # Vim expects int, not bool
        if self.type is not None:
            d["type"] = self.type
        if self.nr is not None:
            d["nr"] = self.nr
        if self.pattern is not None:
            d["pattern"] = self.pattern
        if not self.valid:
            d["valid"] = 0  # default is 1 in Vim, so only override on False
        if self.end_lnum is not None:
            d["end_lnum"] = self.end_lnum
        if self.end_col is not None:
            d["end_col"] = self.end_col
        return d

    @classmethod
    def _to_filename(cls, raw_filename: str, cwd: Path | None) -> str:
        path_obj = Path(raw_filename)
        if not path_obj.is_absolute():
            if cwd is None:
                raise ValueError(f"{cwd} is not given, but relative path is given.")
            abs_filename = str(cwd / path_obj)
        else:
            abs_filename = str(path_obj)
        return abs_filename

    @classmethod
    def from_dict(cls, d: Mapping[str, Any], cwd: Path | str) -> Self:
        if isinstance(cwd, str):
            cwd = Path(cwd)
        return cls(
            filename=cls._to_filename(d["filename"], cwd),
            lnum=int(d.get("lnum", 1)),
            col=int(d.get("col", 1)),
            text=d.get("text", ""),
            vcol=bool(d.get("vcol", 0)),
            type=d.get("type"),
            nr=d.get("nr"),
            pattern=d.get("pattern"),
            valid=bool(d.get("valid", 1)),
            end_lnum=d.get("end_lnum"),
            end_col=d.get("end_col"),
        )

    @property
    def cursor(self) -> CursorPosition:
        return CursorPosition(self.lnum - 1, self.col - 1)

@dataclass
class QuickFixState:
    """Represents the selection state of quickfix.
    """
    index: int | None # 0-based. if `size` == 0, then index is None
    size: int

    def __post_init__(self):
        if self.size < 0:
            raise ValueError("QuickFixState: size must not be negative. ")
        if self.size == 0:
            self.index = None
        if 0 < self.size:
            if self.index is None:
                self.index = 0
        if self.index: 
            self.index = self.index % self.size

