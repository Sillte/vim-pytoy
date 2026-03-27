from typing import Protocol, Any, Sequence, Self
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixRecord, QuickfixState
from pytoy.shared.ui.pytoy_quickfix.protocol import PytoyQuickfixUIProtocol


class PytoyQuickfixDummyUI(PytoyQuickfixUIProtocol):

    def __init__(self) -> None:
        self._records: list[QuickfixRecord] = []
        self._index: int | None = None

    def set_records(self, records: Sequence[QuickfixRecord]) -> QuickfixState:
        self._records = list(records)
        self._index = 0 if self._records else None
        return self.state

    def open(self) -> None:
        pass

    def close(self) -> None:
        self._records = []

    def jump(self, state: QuickfixState) -> QuickfixRecord | None:
        if state.index is None:
            return None
        if not self._records:
            return None
        if state.index < 0 or state.index >= len(self._records):
            return None

        self._index = state.index
        return self._records[state.index]

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        return self._records

    @property
    def state(self) -> QuickfixState:
        return QuickfixState(index=self._index, size=len(self._records))

