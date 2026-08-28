from dataclasses import dataclass
from typing import Literal, Self

LEVEL = Literal["info", "warning", "error"]


@dataclass
class NotificationParam:
    level: LEVEL

    # NOTE:
    # If possible, it try to use `timeout`,
    # For example, `vscode` cannot specify the `timeout`.
    # The infinity time is represented by negative number.

    timeout: int | None = None

    @classmethod
    def from_level(cls, level: LEVEL = "info") -> Self:
        return cls(level=level, timeout=None)
