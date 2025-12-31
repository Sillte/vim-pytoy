"""2025/6/11: Currently, Quickfix does not work correctly `neovim` + `vscode`, so
it takes workaround.
Due to specification, In case of VSCode, only quickfix-like code is used.
"""


from pathlib import Path
from typing import Sequence, Callable

from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickFixProtocol
from pytoy.ui.pytoy_quickfix.models import QuickFixRecord, QuickFixState
from pytoy.ui.pytoy_quickfix.orchestrators import PytoyQuickFixOrchestrator
from pytoy.ui.pytoy_quickfix.state_resolvers import PytoyQuickFixStateResolver


class PytoyQuickFix:
    def __init__(
        self,
        impl: PytoyQuickFixProtocol | None = None,
        *,
        name: str | None = "$default",
    ):
        if impl is None:
            if name is None:
                raise ValueError("impl or name must be set.")
            impl = _get_orchestrator(name)
        self._impl = impl

    @property
    def impl(self) -> PytoyQuickFixProtocol:
        return self._impl

    def set_records(self, records:  Sequence[QuickFixRecord]) -> QuickFixState:
        return self.impl.set_records(records)

    def close(self) -> None:
        return self.impl.close()

    def open(self ) -> None:
        return self.impl.open()

    def jump(self, state: int | QuickFixState | None = None) -> QuickFixRecord | None:
        return self.impl.jump(state)

    def move(self, diff_index: int) -> QuickFixRecord | None:
        return self.impl.move(diff_index)

    def next(self) -> QuickFixRecord | None:
        return self.move(+1)

    def prev(self) -> QuickFixRecord | None:
        return self.move(-1)


_quickfix_cache = dict()


def _get_orchestrator(name: str) -> PytoyQuickFixProtocol:
    if name in _quickfix_cache:
        return _quickfix_cache[name]

    ui_enum = get_ui_enum()

    def make_vscode():
        from pytoy.ui.pytoy_quickfix.impl_vscode import PytoyQuickFixVSCodeUI
        return PytoyQuickFixOrchestrator(PytoyQuickFixStateResolver(), PytoyQuickFixVSCodeUI())

    def make_vim():
        from pytoy.ui.pytoy_quickfix.impl_vim import PytoyQuickFixVimUI
        return PytoyQuickFixOrchestrator(PytoyQuickFixStateResolver(), PytoyQuickFixVimUI())

    creators = {UIEnum.VSCODE: make_vscode, UIEnum.VIM: make_vim, UIEnum.NVIM: make_vim}
    _quickfix_cache[name] = creators[ui_enum]()
    return _quickfix_cache[name]


def get_pytoy_quickfix(name: str) -> PytoyQuickFix:
    impl = _get_orchestrator(name)
    return PytoyQuickFix(impl)


def handle_records(
    pytoy_quickfix: PytoyQuickFix,
    records: Sequence[QuickFixRecord],
    is_open: bool = True,
):
    """When `records` are given, `PytoyQuickFix`  handles them."""
    if records:
        pytoy_quickfix.set_records(records)
        if is_open:
            PytoyQuickFix().open()
    else:
        PytoyQuickFix().close()


type QuickFixRecordRegex = str  # Regarded as 
type QuickFixCreator = QuickFixRecordRegex | Callable[[str], Sequence[QuickFixRecord]]

def to_quickfix_creator(regex: str, cwd: str | Path) -> Callable[[str], Sequence[QuickFixRecord]]:
    import re
    pattern = re.compile(regex)
    def creator(content: str) -> Sequence[QuickFixRecord]:
        records = []
        lines = content.split("\n")
        for line in lines:
            m = pattern.match(line)
            if m:
                row = m.groupdict()
                record = QuickFixRecord.from_dict(row, cwd)
                records.append(record)
        return records
    return creator


if __name__ == "__main__":
    pass
