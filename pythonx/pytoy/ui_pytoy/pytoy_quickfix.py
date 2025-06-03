import vim
import json
from pytoy.ui_pytoy.ui_enum import get_ui_enum, UIEnum
from shlex import quote

class PytoyQuickFix:
    @classmethod
    def setlist(cls, records: list[dict], request_win_id: int | None = None): 
        """ 
        1. When `win_id` is None it is regarded as `quickfix`.
        2. When `records` is empty,  
        """

        win_id = cls._solve_winid(request_win_id)

        if not records:
            cls.close(win_id)

        # [TODO]: this escape is really ok...?
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
            
