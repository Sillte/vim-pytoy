"""Exectuor for `Python`. 
"""
import vim
import re

from pytoy.ui_utils import to_buffer_number, store_window
from pytoy.func_utils import PytoyVimFunctions, with_return
from pytoy.executors import BufferExecutor


class PythonExecutor(BufferExecutor):
    def prepare(self):
        # I do not need to return any `dict` for customization. 
        # But, it requires `win_id` at `on_closed`. 
        self.win_id = vim.eval("win_getid()")

    def on_closed(self): 
        # vim.Function("setloclist") seems to more appropriate, 
        # but it does not work correctly with Python 3.9. 
        setloclist = vim.bindeval('function("setloclist")')

        error_msg = "\n".join(self.stderr)
        if error_msg:
            qflist = self._make_qflist(error_msg)
            setloclist(self.win_id, qflist)  
        else:
            setloclist(self.win_id, [])  # Reset `LocationList`.
            with store_window():
                vim.eval(f"win_gotoid({self.win_id})")
                vim.command(f"lclose")

            nr = int(vim.eval(f'bufwinnr({self.stderr.number})'))
            if 0 <= nr:
                vim.command(f':{nr}close')

            # Scrolling output window
            with store_window():
                stdout_id = vim.eval(f"bufwinid({self.stdout.number})")
                vim.command(f"call win_gotoid({stdout_id})")
                vim.command(f"normal zb")

    def _make_qflist(self, string):
        _pattern = re.compile(r'\s+File "(.+)", line (\d+)')
        result = list()
        lines = string.split("\n")
        index = 0
        while index < len(lines): 
            infos = _pattern.findall(lines[index])
            if infos:
                filename, lnum = infos[0]
                row = dict()
                row["filename"] = filename
                row["lnum"] = lnum
                index += 1
                text = lines[index].strip()
                row["text"] = text
                result.append(row)
            index += 1
        result = list(reversed(result))
        return result

