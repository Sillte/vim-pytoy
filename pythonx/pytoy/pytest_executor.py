import re
from typing import Dict, List

import vim

from pytoy.executors import BufferExecutor

from pytoy.ui_utils import to_buffer_number, init_buffer, create_window, store_window, to_buffer
from pytoy.pytest_utils import PytestDecipher, ScriptDecipher

class PytestExecutor(BufferExecutor):

    def runall(self, stdout):
        """Execute `naive`, `pytest`.  
        """
        command = "pytest"
        init_buffer(stdout)
        return super().run(command, stdout)

    def runfile(self, path, stdout):
        """Execute `pytest` for only one file.
        """
        command = f'pytest "{path}"'
        init_buffer(stdout)
        return super().run(command, stdout)

    def runfunc(self, path, line, stdout):
        """Execute `pytest` for only one function. 
        """
        init_buffer(stdout)
        instance = ScriptDecipher.from_path(path)
        target = instance.pick(line)
        if not target:
            raise ValueError("Specified `path` and `line` is invalid in `PytestExecutor`.")
        command = target.command
        # Options can be added to `command`. 
        command = f"{command} --capture=no --quiet"
        stdout = to_buffer(stdout)
        stdout[0] = command
        return super().run(command, stdout)


    def prepare(self):
        # I do not need to return any `dict` for customization.
        # But, it requires `win_id` at `on_closed`.
        self.win_id = vim.eval("win_getid()")
        return None

    def on_closed(self): 
        # vim.Function("setloclist") seems to more appropriate, 
        # but it does not work correctly with Python 3.9. 
        setloclist = vim.bindeval('function("setloclist")')
        messages = "\n".join(line for line in self.stdout)
        qflist = self._make_qflist(messages)
        if qflist:
            setloclist(self.win_id, qflist)  
        else:
            with store_window():
                vim.eval(f"win_gotoid({self.win_id})")
                vim.command(f"lclose")

        # Scrolling output window
        with store_window():
            stdout_id = vim.eval(f"bufwinid({self.stdout.number})")
            vim.command(f"call win_gotoid({stdout_id})")
            vim.command(f"normal zb")
        
    def _make_qflist(self, string):
        records = PytestDecipher(string).records
        return records
