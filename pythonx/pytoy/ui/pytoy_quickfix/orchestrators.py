from pytoy.ui.pytoy_quickfix.models import QuickFixRecord, QuickFixState
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickFixStateResolverProtocol, PytoyQuickFixUIProtocol, PytoyQuickFixProtocol


from typing import Sequence


class PytoyQuickFixOrchestrator(PytoyQuickFixProtocol):
    def __init__(self,
                 state_resolver: PytoyQuickFixStateResolverProtocol,
                 ui_impl: PytoyQuickFixUIProtocol):
        self._state_resolver = state_resolver
        self._ui_impl = ui_impl

    def set_records(self, records: Sequence[QuickFixRecord]) -> QuickFixState:
        return self.ui.set_records(records)

    def close(self) -> None:
        self.ui.close()

    def open(self):
        self.ui.open()

    def jump(self, state: int | QuickFixState | None = None) -> QuickFixRecord | None:
        state = self._to_state(state)
        return self.ui.jump(state)

    def move(self, diff_index: int) -> QuickFixRecord | None:
        base_state = self.state
        if base_state is None:
            raise ValueError("This quickfix is invalid state.")
        state = self.state_resolver.shift_index(base_state, diff_index)
        return self.jump(state)

    def prev(self) -> QuickFixRecord | None:
        return self.move(-1)

    def next(self) -> QuickFixRecord | None:
        return self.move(+1)

    def _to_state(self, arg: int | QuickFixState | None) -> QuickFixState:
        if isinstance(arg, QuickFixState):
            state = arg
        elif arg is None:
            state = self.state
            if state is None:
                raise ValueError(f"This QuickFix is invalid state.")
        elif isinstance(arg, int):
            state = self._index_to_state(arg)
        else:
            raise TypeError(f"Invaild argments for `QuickFixState`.")
        return state

    def _index_to_state(self, index: int) -> QuickFixState:
        state = self.state
        if state is None:
            raise ValueError(f"This QuickFix is invalid state.")
        if state.size == 0:
            raise ValueError(f"The size of QuickFix is 0")
        return self.state_resolver.fix_index(state, index)

    @property
    def state_resolver(self) -> PytoyQuickFixStateResolverProtocol:
        return self._state_resolver

    @property
    def ui(self) -> PytoyQuickFixUIProtocol:
        return self._ui_impl

    @property
    def records(self) -> Sequence[QuickFixRecord]:
        return self.ui.records

    @property
    def state(self) -> QuickFixState | None:
        state = self.ui.state
        return state

    @property
    def index(self) -> int | None:
        state = self.ui.state
        if not state:
            return None
        return state.index