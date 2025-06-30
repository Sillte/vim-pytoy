"""2025/6/11: Currently, Quickfix does not work correctly `neovim` + `vscode`, so  
it takes workaround. 
Due to specification, In case of VSCode, only quickfix-like code is used.  
"""

from pathlib import Path
import vim
import copy
from typing import Protocol, Any

import json
from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.infra.timertask import TimerTask

from shlex import quote


class PytoyQuickFixProtocol(Protocol):
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


class PytoyQuickFixNormal(PytoyQuickFixProtocol):
    def setlist(self, records: list[dict], win_id: int | None = None):
        # This is NOT smart code,
        # If `value` is `complex` type, it may cause inconsistency of the data type.
        records = [
            {
                key: str(value).replace("'", '"')
                for key, value in row.items()
                if isinstance(value, str)
            }
            for row in records
        ]
        safe_json = quote(json.dumps(records))
        if win_id is None:
            vim.command(f"call setqflist(json_decode({safe_json}))")
        else:
            vim.command(f"call setloclist({win_id}, json_decode({safe_json}))")

    def getlist(self, win_id: int | None = None):
        """
        1. When `win_id` is None it is regarded as `quickfix`.
        2. When `records` is empty,
        """
        if win_id is None:
            return vim.eval("call getqflist()")
        else:
            return vim.eval(f"call getloclist({win_id})")

    def close(self, win_id: int | None = None):
        if win_id is None:
            vim.command("cclose")
            vim.command("call setqflist([])")
        else:
            from pytoy.ui.vim import store_window

            vim.command(f"call setloclist({win_id}, [])")
            with store_window():
                vim.command("lclose")

    def open(self, win_id: int | None = None):
        if win_id is None:
            vim.command("copen")
        else:
            vim.eval(f"win_gotoid({win_id})")
            vim.command("lopen")

    def go(self, idx: int | None = None, win_id: int | None = None) -> None:
        size = int(vim.eval("getqflist({'size': 0})")["size"])
        if not size:
            return
        if idx is not None:
            idx = (idx - 1) % size + 1
            if win_id is None:
                vim.command(f"call setqflist([], 'r', {{'idx': {idx} }})")
            else:
                vim.command(f"call setloclist({win_id}, [], 'r', {{'idx': {idx} }})")
        if win_id is None:
            vim.command("cc")
        else:
            vim.command("ll")

    def next(self, win_id: int | None = None) -> None:
        if win_id is None:
            vim.command("cnext")
        else:
            vim.command("lnext")

    def prev(self, win_id: int | None = None) -> None:
        if win_id is None:
            vim.command("cprev")
        else:
            vim.command("lprev")


class PytoyQuickFixVSCode(PytoyQuickFixProtocol):
    def __init__(
        self,
    ):
        self.records = []
        self.current_idx: int | None = None  # It starts from 1.

    def _convert_filename(self, basepath: Path, record: dict):
        filename = record.get("filename")
        if not filename:
            filename = basepath
        filename = Path(filename)
        if filename.is_absolute():
            record["filename"] = filename.as_posix()
        else:
            record["filename"] = (basepath / filename).resolve().as_posix()
        return record

    def setlist(self, records: list[dict], win_id: int | None = None):
        if win_id is None:
            basepath = Path(vim.eval(f"getcwd()"))
        else:
            basepath = Path(vim.eval(f"getcwd({win_id})"))

        records = [self._convert_filename(basepath, record) for record in records]
        self.records = records
        if not records:
            self.current_idx = None
        else:
            self.current_idx = 1

    def getlist(self, win_id: int | None = None):
        return copy.deepcopy(self.records)

    def close(self, win_id: int | None = None):
        self.records = []
        self.current_idx = None

    def open(self, win_id: int | None = None):
        pass

    def go(self, idx: int | None = None, win_id: int | None = None) -> None:
        if self.current_idx is None:
            print("QuickFix is not SET.")
            return
        self._update_cursor(diff_idx=0, fixed_idx=idx)

    def next(self, win_id: int | None = None):
        if self.current_idx is None:
            print("QuickFix is not SET.")
            return
        self._update_cursor(diff_idx=+1)

    def prev(self, win_id: int | None = None):
        if self.current_idx is None:
            print("QuickFix is not SET.")
            return
        self._update_cursor(diff_idx=-1)

    def _move_idx(
        self, diff_idx: int = 0, *, fixed_idx: int | None = None
    ) -> dict | None:
        """
        1. Move `idx` of Quicklist per `diff_idx`.
        2. If fixed_idx is set, this number is set to
        3. Return the `record` of the moved `idx`.
        """
        records = self.records
        length = len(records)
        if not length:
            return None

        current_idx = self.current_idx
        assert current_idx is not None

        current_idx += diff_idx
        if fixed_idx is not None:
            current_idx = fixed_idx
        if 1 < length:
            current_idx = (current_idx - 1) % length + 1
        else:
            current_idx = 1

        self.current_idx = current_idx

        record = records[current_idx - 1]
        return record

    def _update_cursor(self, diff_idx: int = 0, *, fixed_idx: int | None = None):
        """For VSCODE, this is the unified interface for `next`, `prev` and `go`"""
        record = self._move_idx(diff_idx=diff_idx, fixed_idx=fixed_idx)
        if not record:
            print("No record in QuickFix.")
            return
        path = Path(record["filename"])
        vim.command(f"Edit {path.as_posix()}")
        lnum, col = int(record.get("lnum", 1)), int(record.get("col", 1))

        length = len(self.records)
        idx = self.current_idx
        text = record.get("text", "")

        def func():
            print(f"({idx}/{length}):{text}", flush=True)
            vim.command(f"call cursor({lnum}, {col})")

        TimerTask.execute_oneshot(func, 300)


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
        return PytoyQuickFixVSCode()

    def make_vim():
        return PytoyQuickFixNormal()

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
