import vim

import json
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickFixProtocol

from shlex import quote


class PytoyQuickFixVim(PytoyQuickFixProtocol):
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
            vim.command(f"call setloclist({win_id}, [])")

            current_win = int(vim.eval("win_getid()"))

            if current_win != win_id:
                vim.command(f"call win_gotoid({win_id})")
                vim.command("lclose")
                vim.command("wincmd p")
            else:
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
