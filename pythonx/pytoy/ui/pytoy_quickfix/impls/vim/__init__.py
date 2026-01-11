import vim
from pathlib import Path
from typing import Sequence, Mapping, Any

import json
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickfixProtocol, PytoyQuickfixUIProtocol
from pytoy.ui.pytoy_quickfix.models import QuickfixRecord, QuickfixState

from shlex import quote


class PytoyQuickfixVimUI(PytoyQuickfixUIProtocol):

    def set_records(self, records:  Sequence[QuickfixRecord]) -> QuickfixState:
        self._records = records
        rows = [record.to_dict() for record in records]
        safe_literal = vim.eval(f"string({json.dumps(rows)})")
        vim.command(f"call setqflist({safe_literal})")
        return self.state

    def open(self) -> None:
        vim.command("copen")

    def close(self) -> None:
        vim.command("cclose")
        vim.command("call setqflist([])")

    def jump(self, state: QuickfixState) -> QuickfixRecord | None:
        index = state.index
        if index is None:
            raise ValueError("State is illegal.")
        if state.size == 0:
            raise ValueError("Records of Quick fix is not set.")
        vim_index = index + 1 # 1-based.
        vim.command(f"call setqflist([], 'r', {{'idx': {vim_index} }})")
        res = vim.eval(f"getqflist({{'idx': {vim_index}, 'items': 1}})")

        if not res or not res.get("items"):
            # "Failed to fetch record at index {vim_index}"
            return None 
            raise RuntimeError(f"Failed to fetch record at index {vim_index}")
        record_dict = res["items"][0]
        record = self._from_dict_to_record(record_dict)
        if not record.valid:
            print("Invaid record in Quickfix")
            return record
        # 3. 実際にジャンプ（cc）を実行
        vim.command("cc")
        return record

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        dict_list = vim.eval("call getqflist()")
        return [self._from_dict_to_record(elem) for elem in dict_list]

    @property
    def state(self) -> QuickfixState:
        qf_info = vim.eval("getqflist({'idx': 0, 'size': 0})")
        size = int(qf_info["size"])
        v_idx = int(qf_info["idx"]) # 1-based
        # v_idx が 0 の場合はリストが空
        p_idx = (v_idx - 1) if v_idx > 0 else None
        return QuickfixState(index=p_idx, size=size)


    def _from_dict_to_record(self, data: dict[str, Any]) -> QuickfixRecord:
        bufnr = data.get("bufnr", 0)
        filename = vim.eval(f"fnamemodify(bufname({bufnr}), ':p')")
        data["filename"] = filename
        if bufnr == 0:
            data["valid"] = False
        # Estimated `cwd`, if `filename` is absolute, it is not necessary. 
        cwd = Path(vim.eval("getcwd()"))
        return QuickfixRecord.from_dict(data, cwd)


class PytoyLocationListVimUI(PytoyQuickfixUIProtocol):
    def __init__(self, win_id: int):
        self._win_id = win_id

    @property
    def win_id(self) -> int:
        return self._win_id

    def set_records(self, records: Sequence[QuickfixRecord]) -> QuickfixState:
        """Set records to the location list and open the window."""
        rows = [record.to_dict() for record in records]
        safe_literal = vim.eval(f"string({json.dumps(rows)})")
        # Set to specific window's location list
        vim.command(f"call setloclist({self.win_id}, {safe_literal})")

        # Move to the window and open location list window
        current_win = int(vim.eval("win_getid()"))
        if current_win != self.win_id:
            vim.command(f"call win_gotoid({self.win_id})")
            vim.command("lopen")
            vim.command("wincmd p") # Back to original window
        else:
            vim.command("lopen")
        return self.state

    def open(self) -> None:
        vim.eval(f"win_gotoid({self.win_id})")
        vim.command("lopen")
        vim.command("wincmd p")

    def close(self) -> None:
        """Close the location list and clear its content."""
        vim.command(f"call setloclist({self.win_id}, [])")
        
        current_win = int(vim.eval("win_getid()"))
        if current_win != self.win_id:
            vim.command(f"call win_gotoid({self.win_id})")
            vim.command("lclose")
            vim.command("wincmd p")
        else:
            vim.command("lclose")

    def jump(self, state: QuickfixState) -> QuickfixRecord:
        """Jump to the specific index in the location list."""
        if state.index is None:
            raise ValueError("Index of state is None.")

        # Location list index is 1-based
        vim_index = state.index + 1
        # 'r' action to update only the current index
        vim.command(f"call setloclist({self.win_id}, [], 'r', {{'idx': {vim_index}}})")

        # Execute 'll' in the target window context
        current_win = int(vim.eval("win_getid()"))
        if current_win != self.win_id:
            vim.command(f"call win_gotoid({self.win_id})")

        res = vim.eval(f"getloclist({self.win_id}, {{'idx': {vim_index}, 'items': 1}})")

        if not res or not res.get("items"):
            raise RuntimeError(f"Failed to fetch location list record at index {vim_index}")
        record_dict = res["items"][0]
        record = self._from_dict_to_record(record_dict)

        vim.command("ll")
        return record

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        """Fetch current records from the location list."""
        dict_list = vim.eval(f"getloclist({self.win_id})")
        return [self._from_dict_to_record(elem) for elem in dict_list]

    @property
    def state(self) -> QuickfixState:
        """Fetch current state (index/size) from the location list."""
        # Note the second argument { 'idx': 0, 'size': 0 } to get specific info
        info = vim.eval(f"getloclist({self.win_id}, {{'idx': 0, 'size': 0}})")
        size = int(info["size"])
        v_idx = int(info["idx"]) # 1-based
        
        p_idx = (v_idx - 1) if v_idx > 0 else None
        return QuickfixState(index=p_idx, size=size)

    def _from_dict_to_record(self, data: dict[str, Any]) -> QuickfixRecord:
        bufnr = data.get("bufnr", 0)
        filename = vim.eval(f"fnamemodify(bufname({bufnr}), ':p')")
        data["filename"] = filename
        if bufnr == 0:
            data["valid"] = False
        # Estimated `cwd`, if `filename` is absolute, it is not necessary. 
        cwd = Path(vim.eval(f"getcwd({self.win_id})"))
        return QuickfixRecord.from_dict(data, cwd)
