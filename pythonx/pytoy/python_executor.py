"""Exectuor for `Python`. 
"""
import vim
import json
import re
from shlex import quote

from pytoy.executors import BufferExecutor
from pytoy.ui_utils import init_buffer, store_window

# `set_default_execution_mode` is carried out only in `__init__.py`
from pytoy.environment_manager import EnvironmentManager


from pytoy.ui_pytoy import PytoyBuffer

class PythonExecutor(BufferExecutor):
    def run(self, path, stdout: PytoyBuffer, stderr: PytoyBuffer, *, cwd=None, env=None, force_uv=None):
        """Execute `"""
        if cwd is None:
            cwd = vim.eval("getcwd()")
            # (2022/02/06) I cannot understand, but may `cwd` be bytes.
            try:
                cwd = cwd.decode("utf-8")
            except:
                pass

        # States of class. They are used at `prepare`.
        self.run_path = path
        self.run_cwd = cwd

        command = f'python -u -X utf8 "{path}"'
        wrapper = EnvironmentManager().get_command_wrapper(force_uv=force_uv)

        return super().run(command, stdout, stderr, command_wrapper=wrapper, env=env)

    def rerun(self, stdout, stderr, force_uv=None):
        """Execute the previous `path`."""
        if not hasattr(self, "run_path"):
            raise RuntimeError("Previous file is not existent.")
        cwd = self.run_cwd
        return self.run(self.run_path, stdout, stderr, cwd=cwd, force_uv=force_uv)

    def prepare(self):
        self.win_id = vim.eval("win_getid()")
        options = {"cwd": str(self.run_cwd)}
        return options

    def on_closed(self):
        assert self.stdout is not None 
        assert self.stderr is not None 
        def _setloclist(win_id: int, records: list[dict]):
            import json 
            from shlex import quote
            safe_json = quote(json.dumps(records))
            vim.command(f"call setloclist({win_id}, json_decode({safe_json}))")

        error_msg = self.stderr.content.strip()
        qflist = self._make_qflist(error_msg)

        if qflist:
            _setloclist(self.win_id, qflist)
        else:
            _setloclist(self.win_id, [])  # Reset `LocationList`.
            with store_window():
                vim.eval(f"win_gotoid({self.win_id})")
                vim.command(f"lclose")

            self.stderr.hide()

            ## Scrolling output window
            with store_window():
                self.stdout.focus()
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
