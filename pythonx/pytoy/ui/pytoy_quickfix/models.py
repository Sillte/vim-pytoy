from dataclasses import dataclass
from typing import Any, Self

@dataclass
class QuickFixRecord:
    """Record of QuickFix. 
    """
    # Required parameters
    filename: str
    lnum: int
    col: int = 1
    text: str = ""
    
    # optional parameters
    vcol: bool = False
    type: str | None = None     # "E", "W", "I", "N" など
    nr: int | None  = None       # エラー番号
    pattern: str | None = None  # 正規表現パターン
    valid: bool = True
    
    end_lnum: int | None = None
    end_col: int | None = None
    
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
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(
            filename=d["filename"],
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