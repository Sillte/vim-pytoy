from typing import Protocol, Any


class PytoyQuickFixProtocol(Protocol):
    """QuickFix-like Protocol."""

    def setlist(self, records: list[dict], win_id: int | None = None) -> None:
        ...

    def getlist(self, win_id: int | None = None) -> list[dict[str, Any]]:
        ...

    def close(self, win_id: int | None = None) -> None:
        ...

    def open(self, win_id: int | None = None) -> None:
        ...

    def go(self, idx: int | None = None, win_id: int | None = None) -> None:
        ...

    def next(self, win_id: int | None = None) -> None:
        ...

    def prev(self, win_id: int | None = None) -> None:
        ...
