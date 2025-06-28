"""Exectuor for `Python`. 
"""
import vim
import json
import re
from shlex import quote

from pytoy.lib_tools.buffer_executor import BufferExecutor

# `set_default_execution_mode` is carried out only in `__init__.py`
from pytoy.environment_manager import EnvironmentManager


from pytoy.ui import PytoyBuffer, PytoyQuickFix

class PythonExecutor(BufferExecutor):
    def runfile(self, path, stdout: PytoyBuffer, stderr: PytoyBuffer, *, cwd=None, env=None, force_uv=None):
        """Execute `"""
        if cwd is None:
            cwd = vim.eval("getcwd()")

        # States of class. They are used at `prepare`.
        self.run_path = path
        self.run_cwd = cwd

        command = f'python -u -X utf8 "{path}"'
        wrapper = EnvironmentManager().get_command_wrapper(force_uv=force_uv)

        return super().run(command, stdout, stderr, command_wrapper=wrapper, cwd=cwd, env=env)

    def rerun(self, stdout, stderr, force_uv=None):
        """Execute the previous `path`."""
        if not hasattr(self, "run_path"):
            raise RuntimeError("Previous file is not existent.")
        cwd = self.run_cwd
        return self.runfile(self.run_path, stdout, stderr, cwd=cwd, force_uv=force_uv)

    def prepare(self):
        self.win_id = vim.eval("win_getid()")

    def on_closed(self):
        assert self.stdout is not None 
        assert self.stderr is not None 

        error_msg = self.stderr.content.strip()
        qflist = self._make_qflist(error_msg)

        if qflist:
            PytoyQuickFix().setlist(qflist, self.win_id)
        else:
            PytoyQuickFix().close(self.win_id)
        if not error_msg:
            self.stderr.hide()


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
