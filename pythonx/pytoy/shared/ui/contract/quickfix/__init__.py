from typing import Protocol, Sequence

from pytoy.shared.ui.contract.quickfix.models import QuickfixRecord, QuickfixState


class PytoyQuickfixProtocol(Protocol):
    def set_records(self, records: Sequence[QuickfixRecord]) -> QuickfixState: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def jump(self, state: int | QuickfixState | None = None) -> QuickfixRecord | None: ...

    def move(self, diff_index: int) -> QuickfixRecord | None: ...

    @property
    def records(self) -> Sequence[QuickfixRecord]: ...

    @property
    def state(self) -> QuickfixState | None: ...


class PytoyQuickfixUIProtocol(Protocol):
    def set_records(self, records: Sequence[QuickfixRecord]) -> QuickfixState: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def jump(self, state: QuickfixState) -> QuickfixRecord | None: ...

    @property
    def records(self) -> Sequence[QuickfixRecord]: ...

    @property
    def state(self) -> QuickfixState | None: ...


__all__ = [
    "PytoyQuickfixProtocol",
    "PytoyQuickfixUIProtocol",
    "QuickfixRecord",
    "QuickfixState",
]
