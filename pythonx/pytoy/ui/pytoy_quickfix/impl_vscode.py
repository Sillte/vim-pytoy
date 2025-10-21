from pathlib import Path
import vim
import copy

from pytoy.infra.timertask import TimerTask
from pytoy.ui.pytoy_quickfix.protocol import PytoyQuickFixProtocol
from pytoy.ui import normalize_path


class PytoyQuickFixVSCode(PytoyQuickFixProtocol):
    """
    [NOTE]: VScode does not have concept of `locationlist`.
    So, if `win_id` is given, they are treated as `quickfix` list.
    """

    def __init__(
        self,
    ):
        self.records = []
        self.current_idx: int | None = None  # It starts from 1.

    def _convert_filename(self, basepath: Path, record: dict):
        filename = record.get("filename")
        if not filename:
            filename = basepath
        filename = normalize_path(filename)
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
        basepath = normalize_path(basepath)

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
