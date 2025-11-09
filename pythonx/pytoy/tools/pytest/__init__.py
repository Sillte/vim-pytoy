from pytoy.lib_tools.buffer_executor import BufferExecutor

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import PytoyBuffer, PytoyQuickFix, handle_records
from pytoy.tools.pytest.utils import PytestDecipher, ScriptDecipher


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

    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content
        qflist = self._make_qflist(messages)
        handle_records(PytoyQuickFix(cwd=self.cwd), qflist, win_id=None, is_open=True)

    def _make_qflist(self, string):
        records = PytestDecipher(string).records
        return records
