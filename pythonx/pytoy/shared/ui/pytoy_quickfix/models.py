from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class QuickfixQuery:
    kind: str | None = None

    @classmethod
    def from_any(cls, kind: str | None = None) -> Self:
        return cls(kind=kind)


type QuickfixID = str
