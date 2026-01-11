from pytoy.ui.pytoy_quickfix.models import QuickfixRecord, QuickfixState
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickfixStateResolverProtocol, PytoyQuickfixUIProtocol, PytoyQuickfixProtocol


from typing import Sequence


class PytoyQuickfixOrchestrator(PytoyQuickfixProtocol):
    def __init__(self,
                 state_resolver: PytoyQuickfixStateResolverProtocol,
                 ui_impl: PytoyQuickfixUIProtocol):
        self._state_resolver = state_resolver
        self._ui_impl = ui_impl

    def set_records(self, records: Sequence[QuickfixRecord]) -> QuickfixState:
        return self.ui.set_records(records)

    def close(self) -> None:
        self.ui.close()

    def open(self):
        self.ui.open()

    def jump(self, state: int | QuickfixState | None = None) -> QuickfixRecord | None:
        state = self._to_state(state)
        return self.ui.jump(state)

    def move(self, diff_index: int) -> QuickfixRecord | None:
        base_state = self.state
        if base_state is None:
            raise ValueError("This quickfix is invalid state.")
        state = self.state_resolver.shift_index(base_state, diff_index)
        return self.jump(state)

    def prev(self) -> QuickfixRecord | None:
        return self.move(-1)

    def next(self) -> QuickfixRecord | None:
        return self.move(+1)

    def _to_state(self, arg: int | QuickfixState | None) -> QuickfixState:
        if isinstance(arg, QuickfixState):
            state = arg
        elif arg is None:
            state = self.state
            if state is None:
                raise ValueError(f"This Quickfix is invalid state.")
        elif isinstance(arg, int):
            state = self._index_to_state(arg)
        else:
            raise TypeError(f"Invaild argments for `QuickfixState`.")
        return state

    def _index_to_state(self, index: int) -> QuickfixState:
        state = self.state
        if state is None:
            raise ValueError(f"This Quickfix is invalid state.")
        if state.size == 0:
            raise ValueError(f"The size of Quickfix is 0")
        return self.state_resolver.fix_index(state, index)

    @property
    def state_resolver(self) -> PytoyQuickfixStateResolverProtocol:
        return self._state_resolver

    @property
    def ui(self) -> PytoyQuickfixUIProtocol:
        return self._ui_impl

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        return self.ui.records

    @property
    def state(self) -> QuickfixState | None:
        state = self.ui.state
        return state

    @property
    def index(self) -> int | None:
        state = self.ui.state
        if not state:
            return None
        return state.index
