import vim
import re 

from pytoy.executors import BufferExecutor


from pytoy.pytools_utils import PytestDecipher, ScriptDecipher

from pytoy.environment_manager import EnvironmentManager
from pytoy.ui_pytoy import PytoyBuffer, PytoyQuickFix, store_cursor


def _handle_loclist(win_id, records: list[dict], is_open: bool):
    if records:
        PytoyQuickFix.setlist(records, win_id)
        if is_open:
            PytoyQuickFix.open(win_id)
    else:
        PytoyQuickFix.close(win_id)


class PytestExecutor(BufferExecutor):
    def runall(self, stdout: PytoyBuffer, command_wrapper=None):
        """Execute `naive`, `pytest`."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        command = "pytest"

        return super().run(command, stdout, stdout, command_wrapper=command_wrapper)

    def runfile(self, path, stdout, command_wrapper=None):
        """Execute `pytest` for only one file."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        command = f'pytest "{path}"'
        return super().run(command, stdout, stdout, command_wrapper=command_wrapper)

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

        return super().run(command, stdout, stdout, command_wrapper=command_wrapper)

    def prepare(self):
        # I do not need to return any `dict` for customization.
        # But, it requires `win_id` at `on_closed`.
        self.win_id = vim.eval("win_getid()")
        return {}

    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content
        qflist = self._make_qflist(messages)
        _handle_loclist(self.win_id, qflist, is_open=True)

        # Scrolling output window
        with store_cursor():
            assert self.stdout is not None
            self.stdout.focus()
            vim.command("normal zb")

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
        #stdout[0] = command
        return super().run(command, stdout, stdout, command_wrapper=command_wrapper)

    def prepare(self):
        # I do not need to return any `dict` for customization.
        # But, it requires `win_id` at `on_closed`.
        self.win_id = vim.eval("win_getid()")
        return None

    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content

        qflist = self._make_qflist(messages)
        _handle_loclist(self.win_id, qflist, is_open=True)

        # Scrolling output window
        with store_cursor():
            self.stdout.focus()
            vim.command("normal zb")

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


class RuffExecutor(BufferExecutor):
    """Execute Ruff.
    """
    def __init__(self):
        self._pattern = re.compile(r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<text>(.+))")

    def check_file(self, path, stdout, command_wrapper=None):
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        command = f'ruff check "{path}"'
        return super().run(command, stdout, stdout, command_wrapper=command_wrapper)

    def prepare(self):
        # I do not need to return any `dict` for customization.
        # But, it requires `win_id` at `on_closed`.
        self.win_id = vim.eval("win_getid()")
        return None

    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content
        qflist = self._make_qflist(messages)

        _handle_loclist(self.win_id, qflist, is_open=True)


    def _make_qflist(self, string):
        # Record of `mypy`. 
        records = []
        for line in string.split("\n"):
            match = self._pattern.match(line.strip())
            if not match:
                continue
            record = match.groupdict()
            records.append(record)
        return records

