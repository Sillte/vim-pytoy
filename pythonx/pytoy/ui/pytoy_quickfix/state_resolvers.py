from pytoy.ui.pytoy_quickfix.models import QuickfixRecord, QuickfixState
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickfixStateResolverProtocol
from typing import Sequence

class PytoyQuickfixStateResolver(PytoyQuickfixStateResolverProtocol):
    def resolve_record(
        self, 
        records: Sequence[QuickfixRecord],
        state: QuickfixState
    ) -> QuickfixRecord | None:
        """Resolve a record from the state index."""
        if state.index is None:
            return None
        if state.size != len(records):
            raise ValueError("Inconsistency of `size` occurs.")
        return records[state.index]

    def shift_index(self, state: QuickfixState, diff_index: int) -> QuickfixState:
        """Calculate the new state by shifting the index with wrap-around."""
        if state.index is None:
            return state
        return QuickfixState(index=state.index + diff_index, size=state.size)

    def fix_index(self, state: QuickfixState, index: int) -> QuickfixState:
        """Return the state where `index` if fixed."""
        if state.size == 0:
            return state
        return QuickfixState(index=index, size=state.size)