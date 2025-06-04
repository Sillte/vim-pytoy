from pathlib import Path
import vim

import json
from pytoy.ui_pytoy.ui_enum import get_ui_enum, UIEnum
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
                vim.command(f"lclose")

    @classmethod
    def open(cls, request_win_id: int | None = None):
        win_id = cls._solve_winid(request_win_id)

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

   
