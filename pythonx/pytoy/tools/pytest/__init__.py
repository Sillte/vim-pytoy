from pytoy.lib_tools.buffer_executor import BufferJobProtocol, CommandWrapper 
from pytoy.lib_tools.buffer_executor import BufferJobManager, BufferJobCreationParam

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.lib_tools.utils import get_current_directory
from pytoy.ui import PytoyBuffer, PytoyQuickFix, handle_records
from pytoy.tools.pytest.utils import PytestDecipher, ScriptDecipher


class PytestExecutor:
    job_name = "PytestExecutor"

    def runall(self, stdout: PytoyBuffer, command_wrapper=None):
        """Execute `naive`, `pytest`."""
        command = "pytest"
        return self._run(command, stdout, command_wrapper=command_wrapper)

    def runfile(self, path, stdout, command_wrapper=None):
        """Execute `pytest` for only one file."""
        command = f'pytest "{path}"'
        return self._run(command, stdout, command_wrapper=command_wrapper)

    def runfunc(self, path, line, stdout, command_wrapper=None):
        """Execute `pytest` for only one function."""
        instance = ScriptDecipher.from_path(path)
        target = instance.pick(line)
        if not target:
            raise ValueError(
                "Specified `path` and `line` is invalid in `PytestExecutor`."
            )
        command = target.command
        # Options can be added to `command`.
        command = f"{command} --capture=no --quiet"

        return self._run(command, stdout, command_wrapper=command_wrapper)
    
    def _run(self, command: str, stdout: PytoyBuffer, command_wrapper: CommandWrapper | None = None) -> None:
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        wrapped_command = command_wrapper(command)
        cwd = get_current_directory()
        param = BufferJobCreationParam(command=wrapped_command, stdout=stdout, stderr=stdout, cwd=cwd, on_closed=self.on_closed)
        BufferJobManager.create(self.job_name, param)

    def on_closed(self, buffer_job: BufferJobProtocol) -> None:
        assert buffer_job.stdout is not None
        messages = buffer_job.stdout.content
        qflist = self._make_qflist(messages)
        handle_records(PytoyQuickFix(cwd=buffer_job.cwd), qflist, win_id=None, is_open=True)

    def _make_qflist(self, string):
        records = PytestDecipher(string).records
        return records
