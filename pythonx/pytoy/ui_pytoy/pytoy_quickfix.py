"""2025/6/11: Currently, Quickfix does not work correctly `neovim` + `vscode`, so  
it takes workaround. 
Due to specification, In case of VSCode, only quickfix-like code is used.  
"""

from pathlib import Path
import vim
import copy

import json
from pytoy.ui_pytoy.ui_enum import get_ui_enum, UIEnum
from pytoy.timertask_manager import TimerTaskManager

from shlex import quote


class PytoyQuickFixNormal:
    @classmethod
    def setlist(cls, records: list[dict], win_id: int | None = None):
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

    @classmethod
    def getlist(cls, win_id: int | None = None):
        """
        1. When `win_id` is None it is regarded as `quickfix`.
        2. When `records` is empty,
        """
        if win_id is None:
            return vim.eval("call getqflist()")
        else:
            return vim.eval(f"call getloclist({win_id})")

    @classmethod
    def close(cls, win_id: int | None = None):
        if win_id is None:
            vim.command("cclose")
            vim.command("call setqflist([])")
        else:
            from pytoy.ui_utils import store_window

            vim.command(f"call setloclist({win_id}, [])")
            with store_window():
                vim.command("lclose")

    @classmethod
    def open(cls, win_id: int | None = None):
        if win_id is None:
            vim.command("copen")
        else:
            vim.eval(f"win_gotoid({win_id})")
            vim.command("lopen")


class PytoyQuickFixVSCode:
    records: list[dict] = []
    current_idx: int | None = None  # It starts from 1.

    @classmethod
    def setlist(cls, records: list[dict], win_id: int | None = None):
        if win_id is None:
            basepath = Path(vim.eval(f"getcwd()"))
        else:
            basepath = Path(vim.eval(f"getcwd({win_id})"))

        def _convert_filename(record: dict):
            filename = record.get("filename")
            if not filename:
                filename = basepath
            filename = Path(filename)
            if filename.is_absolute():
                record["filename"] = filename.as_posix()
            else:
                record["filename"] = (basepath / filename).resolve().as_posix()
            return record

        for record in records:
            _convert_filename(record)

        cls.records = records
        if not records:
            cls.current_idx = None
        else:
            cls.current_idx = 1

    @classmethod
    def getlist(cls, win_id: int | None = None):
        return copy.deepcopy(cls.records)

    @classmethod
    def close(cls, win_id: int | None = None):
        cls.records = []
        cls.current_idx = None

    @classmethod
    def open(cls, win_id: int | None = None):
        pass


class PytoyQuickFix:
    @classmethod
    def setlist(cls, records: list[dict], win_id: int | None = None):
        if get_ui_enum() == UIEnum.VSCODE:
            return PytoyQuickFixVSCode.setlist(records, win_id)
        else:
            return PytoyQuickFixNormal.setlist(records, win_id)

    @classmethod
    def getlist(cls, win_id: int | None = None):
        if get_ui_enum() == UIEnum.VSCODE:
            return PytoyQuickFixVSCode.getlist(win_id)
        else:
            return PytoyQuickFixNormal.getlist(win_id)

    @classmethod
    def close(cls, win_id: int | None = None):
        if get_ui_enum() == UIEnum.VSCODE:
            return PytoyQuickFixVSCode.close(win_id)
        else:
            return PytoyQuickFixNormal.close(win_id)

    @classmethod
    def open(cls, win_id: int | None = None):
        if get_ui_enum() == UIEnum.VSCODE:
            return PytoyQuickFixVSCode.open(win_id)
        else:
            return PytoyQuickFixNormal.open(win_id)


class QuickFixController:
    """
    When UIEnum.VSCODE, it should work...
    """

    @classmethod
    def go(cls):
        if get_ui_enum() == UIEnum.VSCODE:
            QuickFixControllerVSCode.go()
        else:
            QuickFixControllerNormal.go()

    @classmethod
    def next(cls, is_location: bool | None = None):
        if get_ui_enum() == UIEnum.VSCODE:
            QuickFixControllerVSCode.next()
        else:
            QuickFixControllerNormal.next()

    @classmethod
    def prev(cls, is_location: bool | None = None):
        if get_ui_enum() == UIEnum.VSCODE:
            QuickFixControllerVSCode.prev()
        else:
            QuickFixControllerNormal.prev()


class QuickFixControllerNormal:
    @classmethod
    def go(cls):
        if get_ui_enum() in {UIEnum.VIM, UIEnum.NVIM}:
            is_location = cls._is_location()
            if is_location:
                vim.command("ll")
            else:
                vim.command("cc")
            return

    @classmethod
    def next(cls, is_location: bool | None = None):
        return cls._command("next", is_location=is_location)

    @classmethod
    def prev(cls, is_location: bool | None = None):
        return cls._command("prev", is_location=is_location)

    @classmethod
    def _is_location(cls) -> bool:
        if get_ui_enum() == UIEnum.VSCODE:
            return False
        records = vim.eval("getloclist(0)")
        if records:
            return True
        return False

    @classmethod
    def _command(cls, cmd: str, is_location: bool | None = None):
        if is_location is None:
            is_location = cls._is_location()
        if is_location:
            cmd = f"l{cmd}"
        else:
            cmd = f"c{cmd}"
        vim.command(cmd)


class QuickFixControllerVSCode:
    @classmethod
    def go(cls):
        if PytoyQuickFixVSCode.current_idx is None:
            print("QuickFix is not SET.")
            return
        cls._update_cursor(diff_idx=0)

    @classmethod
    def next(cls, is_location: bool | None = None):
        if PytoyQuickFixVSCode.current_idx is None:
            print("QuickFix is not SET.")
            return
        cls._update_cursor(diff_idx=+1)

    @classmethod
    def prev(cls, is_location: bool | None = None):
        if PytoyQuickFixVSCode.current_idx is None:
            print("QuickFix is not SET.")
            return
        cls._update_cursor(diff_idx=-1)

    @classmethod
    def _move_idx(
        cls, diff_idx: int = 0, *, fixed_idx: int | None = None
    ) -> dict | None:
        """
        1. Move `idx` of Quicklist per `diff_idx`.
        2. If fixed_idx is set, this number is set to
        3. Return the `record` of the moved `idx`.
        """
        records = PytoyQuickFixVSCode.records
        length = len(records)
        if not length:
            return None

        current_idx = PytoyQuickFixVSCode.current_idx
        assert current_idx is not None

        current_idx += diff_idx
        if fixed_idx is not None:
            current_idx = fixed_idx
        if 1 < length:
            current_idx = (current_idx - 1) % length + 1
        else:
            current_idx = 1

        PytoyQuickFixVSCode.current_idx = current_idx

        record = records[current_idx - 1]
        return record

    @classmethod
    def _update_cursor(cls, diff_idx: int = 0, *, fixed_idx: int | None = None):
        """For VSCODE, this is the unified interface for `next`, `prev` and `go`"""
        record = cls._move_idx(diff_idx=diff_idx, fixed_idx=fixed_idx)
        if not record:
            print("No record in QuickFix.")
            return
        path = Path(record["filename"])
        vim.command(f"Edit {path.as_posix()}")
        lnum, col = int(record["lnum"]), int(record["col"])

        length = len(PytoyQuickFixVSCode.records)
        idx = PytoyQuickFixVSCode.current_idx
        text = record.get("text", "")

        def func():
            print(f"({idx}/{length}):{text}", flush=True)
            vim.command(f"call cursor({lnum}, {col})")

        TimerTaskManager.execute_oneshot(func, 300)
