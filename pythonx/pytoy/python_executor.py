"""Exectuor for `Python`. 
"""
import vim
import re

from pytoy.executors import BufferExecutor
from pytoy.ui_utils import init_buffer, store_window

# `set_default_execution_mode` is carried out only in `__init__.py`
from pytoy.pytoy_states import get_default_execution_mode, ExecutionMode


class PythonExecutor(BufferExecutor):
    def run(self, path, stdout, stderr, *, cwd=None, with_uv=None):
        """Execute `"""
        if cwd is None:
            cwd = vim.Function("getcwd")()
            # (2022/02/06) I cannot understand, but may `cwd` be bytes.
            try:
                cwd = cwd.decode("utf-8")
            except:
                pass

        if with_uv is None:
            e_mode = get_default_execution_mode()
            if e_mode == ExecutionMode.WITH_UV:
                with_uv = True
            else:
                with_uv = False

        # States of class. They are used at `prepare`.
        self.run_path = path
        self.run_cwd = cwd

        if with_uv is True:
            command = f'uv run python -u -X utf8 "{path}"'
            directive = f"`uv run python {path}`"
        else:
            command = f'python -u -X utf8 "{path}"'
            directive = f"`python {path}`"

        init_buffer(stdout)
        init_buffer(stderr)
        stdout[0] = directive
        return super().run(command, stdout, stderr)

    def rerun(self, stdout, stderr):
        """Execute the previous `path`."""
        if not hasattr(self, "run_path"):
            raise RuntimeError("Previous file is not existent.")
        cwd = self.run_cwd
        return self.run(self.run_path, stdout, stderr, cwd=cwd)

    def prepare(self):
        self.win_id = vim.eval("win_getid()")
        options = {"cwd": str(self.run_cwd)}
        return options

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

            nr = int(vim.eval(f"bufwinnr({self.stderr.number})"))
            if 0 <= nr:
                vim.command(f":{nr}close")

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
