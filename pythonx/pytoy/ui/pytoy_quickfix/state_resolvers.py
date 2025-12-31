from pytoy.ui.pytoy_quickfix.models import QuickFixRecord, QuickFixState
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickFixStateResolverProtocol
from typing import Sequence

class PytoyQuickFixStateResolver(PytoyQuickFixStateResolverProtocol):
    def resolve_record(
        self, 
        records: Sequence[QuickFixRecord],
        state: QuickFixState
    ) -> QuickFixRecord | None:
        """Resolve a record from the state index."""
        if state.index is None:
            return None
        if state.size != len(records):
            raise ValueError("Inconsistency of `size` occurs.")
        return records[state.index]

    def shift_index(self, state: QuickFixState, diff_index: int) -> QuickFixState:
        """Calculate the new state by shifting the index with wrap-around."""
        if state.index is None:
            return state
        return QuickFixState(index=state.index + diff_index, size=state.size)

    def fix_index(self, state: QuickFixState, index: int) -> QuickFixState:
        """Return the state where `index` if fixed."""
        if state.size == 0:
            return state
        return QuickFixState(index=index, size=state.size)