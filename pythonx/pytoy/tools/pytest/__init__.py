import vim

from pytoy.lib_tools.buffer_executor import BufferExecutor


from pytoy.tools.pytools_utils import PytestDecipher, ScriptDecipher

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import PytoyBuffer, PytoyQuickFix



def _to_quickfix_winid(win_id: int, is_location: bool | None = None) -> int | None:
    if is_location is None:
        is_location = False  # Default behavior.

    if is_location:
        return win_id
    else:
        return None


def _handle_loclist(win_id, records: list[dict], is_open: bool):
    if records:
        PytoyQuickFix().setlist(records, win_id)
        if is_open:
            PytoyQuickFix().open(win_id)
    else:
        PytoyQuickFix().close(win_id)


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

        q_winid = _to_quickfix_winid(self.win_id)
        _handle_loclist(q_winid, qflist, is_open=True)

    def _make_qflist(self, string):
        records = PytestDecipher(string).records
        return records
