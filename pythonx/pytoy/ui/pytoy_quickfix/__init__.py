"""2025/6/11: Currently, Quickfix does not work correctly `neovim` + `vscode`, so
it takes workaround.
Due to specification, In case of VSCode, only quickfix-like code is used.
"""

from typing import Any

from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickFixProtocol


class PytoyQuickFix(PytoyQuickFixProtocol):
    def __init__(
        self,
        impl: PytoyQuickFixProtocol | None = None,
        *,
        name: str | None = "$default",
    ):
        if impl is None:
            if name is None:
                raise ValueError("impl or name must be set.")
            impl = _get_protocol(name)
        self._impl = impl

    @property
    def impl(self) -> PytoyQuickFixProtocol:
        return self._impl

    def setlist(self, records: list[dict], win_id: int | None = None) -> None:
        return self.impl.setlist(records, win_id)

    def getlist(self, win_id: int | None = None) -> list[dict[str, Any]]:
        return self.impl.getlist(win_id)

    def close(self, win_id: int | None = None) -> None:
        return self.impl.close(win_id)

    def open(self, win_id: int | None = None) -> None:
        return self.impl.open(win_id)

    def go(self, idx: int | None = None, win_id: int | None = None) -> None:
        return self.impl.go(idx, win_id)

    def next(self, win_id: int | None = None) -> None:
        return self.impl.next(win_id)

    def prev(self, win_id: int | None = None) -> None:
        return self.impl.prev(win_id)


_quickfix_protocol_cache = dict()


def _get_protocol(name: str) -> PytoyQuickFixProtocol:
    if name in _quickfix_protocol_cache:
        return _quickfix_protocol_cache[name]

    ui_enum = get_ui_enum()

    def make_vscode():
        from pytoy.ui.pytoy_quickfix.impl_vscode import PytoyQuickFixVSCode

        return PytoyQuickFixVSCode()

    def make_vim():
        from pytoy.ui.pytoy_quickfix.impl_vim import PytoyQuickFixVim

        return PytoyQuickFixVim()

    creators = {UIEnum.VSCODE: make_vscode, UIEnum.VIM: make_vim, UIEnum.NVIM: make_vim}
    _quickfix_protocol_cache[name] = creators[ui_enum]()
    return _quickfix_protocol_cache[name]


def get_pytoy_quickfix(name: str) -> PytoyQuickFix:
    impl = _get_protocol(name)
    return PytoyQuickFix(impl)


def handle_records(
    pytoy_quickfix: PytoyQuickFix,
    records: list[dict],
    win_id: int | None = None,
    is_open: bool = True,
):
    """When `records` are given, `PytoyQuickFix`  handles them."""
    if records:
        pytoy_quickfix.setlist(records, win_id=win_id)
        if is_open:
            PytoyQuickFix().open(win_id=win_id)
    else:
        PytoyQuickFix().close(win_id=win_id)


if __name__ == "__main__":
    pass
