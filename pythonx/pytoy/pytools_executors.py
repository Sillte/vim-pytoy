import vim
import re 

from pytoy.executors import BufferExecutor

from pytoy.ui_utils import (
    init_buffer,
    store_window,
    to_buffer,
)
from pytoy.pytools_utils import PytestDecipher, ScriptDecipher

from pytoy.environment_manager import EnvironmentManager


class PytestExecutor(BufferExecutor):
    def runall(self, stdout, command_wrapper=None):
        """Execute `naive`, `pytest`."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        command = "pytest"
        init_buffer(stdout)
        return super().run(command, stdout, command_wrapper=command_wrapper)

    def runfile(self, path, stdout, command_wrapper=None):
        """Execute `pytest` for only one file."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        command = f'pytest "{path}"'
        init_buffer(stdout)
        return super().run(command, stdout, command_wrapper=command_wrapper)

    def runfunc(self, path, line, stdout, command_wrapper=None):
        """Execute `pytest` for only one function."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        instance = ScriptDecipher.from_path(path)
        target = instance.pick(line)
        if not target:
            raise ValueError(
                "Specified `path` and `line` is invalid in `PytestExecutor`."
            )
        command = target.command
        # Options can be added to `command`.
        command = f"{command} --capture=no --quiet"
        init_buffer(stdout)

        stdout = to_buffer(stdout)
        stdout[0] = command
        return super().run(command, stdout, command_wrapper=command_wrapper)

    def prepare(self):
        # I do not need to return any `dict` for customization.
        # But, it requires `win_id` at `on_closed`.
        self.win_id = vim.eval("win_getid()")
        return {}

    def on_closed(self):
        # vim.Function("setloclist") seems to more appropriate,
        # but it does not work correctly with Python 3.9?
        setloclist = vim.bindeval('function("setloclist")')
        assert self.stdout is not None
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
            assert self.stdout is not None
            stdout_id = vim.eval(f"bufwinid({self.stdout.number})")
            vim.command(f"call win_gotoid({stdout_id})")
            vim.command(f"normal zb")

    def _make_qflist(self, string):
        records = PytestDecipher(string).records
        return records



class MypyExecutor(BufferExecutor):
    """Execute Mypy.
    """
    def __init__(self):
        self._pattern = re.compile(r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<_type>(.+)):(?P<text>(.+))")

    def runfile(self, path, stdout, command_wrapper=None):
        """Execute `pytest` for only one file."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        command = f'mypy --show-traceback --show-column-numbers "{path}"'
        stdout = to_buffer(stdout)
        init_buffer(stdout)
        #stdout[0] = command
        return super().run(command, stdout, command_wrapper=command_wrapper)

    def prepare(self):
        # I do not need to return any `dict` for customization.
        # But, it requires `win_id` at `on_closed`.
        self.win_id = vim.eval("win_getid()")
        return None

    def on_closed(self):
        # vim.Function("setloclist") seems to more appropriate,
        # but it does not work correctly with Python 3.9?
        assert self.stdout is not None
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
        # Record of `mypy`. 
        records = []
        for line in string.split("\n"):
            match = self._pattern.match(line.strip())
            if not match:
                continue
            record = match.groupdict()
            record["type"] = record["_type"].strip(" ")[0].upper()
            records.append(record)
        return records
