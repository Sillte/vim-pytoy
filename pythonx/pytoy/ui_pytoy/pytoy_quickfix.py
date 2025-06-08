from pathlib import Path
import vim

import json
from pytoy.ui_pytoy.ui_enum import get_ui_enum, UIEnum
from pytoy.timertask_manager import TimerTaskManager

from shlex import quote

class PytoyQuickFix:
    @classmethod
    def setlist(cls, records: list[dict], request_win_id: int | None = None): 
        """ 
        1. When `win_id` is None it is regarded as `quickfix`.
        2. When `records` is empty, it is closed.  
        """
                    
        win_id = cls._solve_winid(request_win_id)

        if not records:
            cls.close(win_id)
            return 

        if win_id != request_win_id and win_id is None:
            # setloc -> setqf
            lcd = Path(vim.eval(f"getcwd({request_win_id})"))
            cd = Path(vim.eval(f"getcwd()"))
            records = cls._solve_cwd(records, lcd, cd)

        # If the json string does not include single quotations, 
        # it is easy for `quote` to do the work by surrounding the string
        # one pair of `single` quote. 
        records = [{key: str(value).replace("'", '"') for key, value in row.items()} for row in records]
        safe_json = quote(json.dumps(records))
        if win_id is None:
            vim.command(f"call setqflist(json_decode({safe_json}))")
        else:
            vim.command(f'call setloclist({win_id}, json_decode({safe_json}))')

    @classmethod
    def getlist(cls, request_win_id: int | None = None): 
        """ 
        1. When `win_id` is None it is regarded as `quickfix`.
        2. When `records` is empty,  
        """

        win_id = cls._solve_winid(request_win_id)

        if win_id is None:
            return vim.command("call getqflist()")
        else:
            return vim.command(f"call getloclist({win_id})")

    @classmethod
    def close(cls, request_win_id: int | None = None):
        win_id = cls._solve_winid(request_win_id)

        if win_id is None:
            vim.command("cclose")
            vim.command("call setqflist([])")
            return 
        else:
            # This should not be called in neovim+vscode 
            from pytoy.ui_utils import store_window
            vim.command(f"call setloclist({win_id}, [])")
            with store_window(): 
                vim.eval(f"win_gotoid({win_id})")
                vim.command("lclose")

    @classmethod
    def open(cls, request_win_id: int | None = None):
        win_id = cls._solve_winid(request_win_id)
        
        if get_ui_enum() == UIEnum.VSCODE:
            assert win_id is None, "No locationlist for VSCode."
            records = vim.eval("getqflist()")
            if not records:
                print("Empty QuickFix List, Skipped the open the window", flush=True)
                return 

        if win_id is None: 
            vim.command("copen")
        else:
            vim.eval(f"win_gotoid({win_id})")
            vim.command("lopen")


    @classmethod
    def _solve_winid(cls, request_win_id: int | None = None): 
        if get_ui_enum() == UIEnum.VSCODE:
            win_id = None
        else:
            win_id = request_win_id
        return win_id

    @classmethod
    def _solve_cwd(cls, records: list[dict], in_origin: Path, out_origin: Path | None): 
        """If records include `filename` and they are regarded
        as relative paths, then, these filename are converted from ones
        whose start is `in_origin` to `output_origin`. 

        When `out_origin` is specified, `filename` becomes the relative path, 
        if not, it becomes the absolute path.
        """
        def _absolute_path_or_none(record: dict) -> Path | None:
            if "filename" in record:
                path = Path(record["filename"])
                if path.is_absolute():
                    return path
                else:
                    try:
                        return (in_origin / path).resolve()
                    except Exception:
                        return path
            return None
       
        def _resolve_path(record: dict, abs_path:Path | None) -> dict:
            if not abs_path:
                return record
            if out_origin:
                try:
                    rel = abs_path.relative_to(out_origin)
                except ValueError:
                    rel = abs_path
                filename = rel.as_posix()
            else:
                filename = abs_path.as_posix()
            record["filename"] = filename
            return record

        abs_files = [_absolute_path_or_none(record) for record in records]
        records = [ _resolve_path(record, abs_path) for record, abs_path in zip(records, abs_files)]
        return records
    

class QuickFixController:
    """
    When UIEnum.VSCODE, it should work...
    """
    @classmethod
    def go(cls):
        if get_ui_enum() in {UIEnum.VIM, UIEnum.NVIM}:
            is_location  = cls._is_location()
            if is_location:
                vim.command("ll")
            else:
                vim.command("cc")
            return 

        # VSCODE:
        records = vim.eval("getqflist()")
        if not records:
            print("Empty QuickFix List, Skipped the open the window", flush=True)
            return 
        idx = int(vim.eval("getqflist({'idx': 0}).idx"))
        record = records[idx - 1]
        bufnr = record.get("bufnr", 0)
        if bufnr:
            vim.command("cc")
        else: 
            vim.command("cc")
            def func():
                vim.command("cc")
            TimerTaskManager.execute_oneshot(func, 300)

    @classmethod
    def next(cls, is_location: bool | None = None):
        if get_ui_enum() in {UIEnum.VIM, UIEnum.NVIM}:
            return cls._command("next", is_location=is_location)

        # In case of VS, we have to consider syncronization of Editor and buffer.
        is_location = False
        #vim.command("cnext | call timer_start(50, { -> execute('cc') })")  # I assume this i also ok.
        vim.command("cnext")
        def func():
            vim.command("cc")
        TimerTaskManager.execute_oneshot(func, 500)


    @classmethod
    def prev(cls, is_location: bool | None = None):
        if get_ui_enum() in {UIEnum.VIM, UIEnum.NVIM}:
            return cls._command("next", is_location=is_location)

        is_location = False
        vim.command("cprev")
        def func():
            vim.command("cc")
        TimerTaskManager.execute_oneshot(func, 500)

    
    @classmethod
    def _is_location(cls) -> bool:
        if get_ui_enum() == UIEnum.VSCODE:
            return False
        records = vim.eval("getloclist(0)")
        if records:
            return True
        return False
    
    @classmethod
    def _command(cls, cmd: str, is_location: bool | None= None):  
        if is_location is None:
            is_location = cls._is_location()
        if is_location:
            cmd = f"l{cmd}"
        else:
            cmd = f"c{cmd}"
        vim.command(cmd)

