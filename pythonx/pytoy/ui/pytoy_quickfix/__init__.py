"""2025/6/11: Currently, Quickfix does not work correctly `neovim` + `vscode`, so
it takes workaround.
Due to specification, In case of VSCode, only quickfix-like code is used.
"""


from pathlib import Path
from typing import Sequence, Callable

from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickfixProtocol
from pytoy.ui.pytoy_quickfix.models import QuickfixRecord, QuickfixState
from pytoy.ui.pytoy_quickfix.orchestrators import PytoyQuickfixOrchestrator
from pytoy.ui.pytoy_quickfix.state_resolvers import PytoyQuickfixStateResolver


class PytoyQuickfix:
    def __init__(
        self,
        impl: PytoyQuickfixProtocol | None = None,
        *,
        name: str | None = "$default",
    ):
        if impl is None:
            if name is None:
                raise ValueError("impl or name must be set.")
            impl = _get_orchestrator(name)
        self._impl = impl

    @property
    def impl(self) -> PytoyQuickfixProtocol:
        return self._impl

    def set_records(self, records:  Sequence[QuickfixRecord]) -> QuickfixState:
        return self.impl.set_records(records)

    def close(self) -> None:
        return self.impl.close()

    def open(self ) -> None:
        return self.impl.open()

    def jump(self, state: int | QuickfixState | None = None) -> QuickfixRecord | None:
        return self.impl.jump(state)

    def move(self, diff_index: int) -> QuickfixRecord | None:
        return self.impl.move(diff_index)

    def next(self) -> QuickfixRecord | None:
        return self.move(+1)

    def prev(self) -> QuickfixRecord | None:
        return self.move(-1)


_quickfix_cache = dict()


def _get_orchestrator(name: str) -> PytoyQuickfixProtocol:
    if name in _quickfix_cache:
        return _quickfix_cache[name]

    ui_enum = get_ui_enum()

    def make_vscode():
        from pytoy.ui.pytoy_quickfix.impls.vscode import PytoyQuickfixVSCodeUI
        return PytoyQuickfixOrchestrator(PytoyQuickfixStateResolver(), PytoyQuickfixVSCodeUI())

    def make_vim():
        from pytoy.ui.pytoy_quickfix.impls.vim import PytoyQuickfixVimUI
        return PytoyQuickfixOrchestrator(PytoyQuickfixStateResolver(), PytoyQuickfixVimUI())

    creators = {UIEnum.VSCODE: make_vscode, UIEnum.VIM: make_vim, UIEnum.NVIM: make_vim}
    _quickfix_cache[name] = creators[ui_enum]()
    return _quickfix_cache[name]


def get_pytoy_quickfix(name: str) -> PytoyQuickfix:
    impl = _get_orchestrator(name)
    return PytoyQuickfix(impl)


def handle_records(
    pytoy_quickfix: PytoyQuickfix,
    records: Sequence[QuickfixRecord],
    is_open: bool = True,
):
    """When `records` are given, `PytoyQuickfix`  handles them."""
    if records:
        pytoy_quickfix.set_records(records)
        if is_open:
            PytoyQuickfix().open()
    else:
        PytoyQuickfix().close()


type QuickfixRecordRegex = str  # Regarded as 
type QuickfixCreator =  Callable[[str], Sequence[QuickfixRecord]]

def to_quickfix_creator(regex: QuickfixRecordRegex | QuickfixCreator, cwd: str | Path) -> QuickfixCreator:
    if callable(regex):
        return regex

    import re
    pattern = re.compile(regex)
    def creator(content: str) -> Sequence[QuickfixRecord]:
        records = []
        lines = content.split("\n")
        for line in lines:
            m = pattern.match(line)
            if m:
                row = m.groupdict()
                record = QuickfixRecord.from_dict(row, cwd)
                records.append(record)
        return records
    return creator


if __name__ == "__main__":
    pass
