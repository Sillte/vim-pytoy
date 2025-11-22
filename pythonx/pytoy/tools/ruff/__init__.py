import re
import subprocess

from pytoy.lib_tools.buffer_executor import BufferJobProtocol  
from pytoy.lib_tools.buffer_executor import BufferJobProtocol, BufferJobManager, BufferJobCreationParam

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.lib_tools.utils import get_current_directory
from pytoy.ui import PytoyQuickFix, handle_records


class RuffExecutor:
    """Execute Ruff."""
    job_name = "RuffExecutor"

    def __init__(self):
        self._pattern = re.compile(
            r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<text>(.+))"
        )

    def check(self, args: str | list, stdout, command_wrapper=None):
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()

        if isinstance(args, list):
            args = " ".join(map(str, args))
        command = f"ruff check {args} --output-format=concise"
        cwd = get_current_directory()
        wrapped_command = command_wrapper(command)
        param = BufferJobCreationParam(command=wrapped_command,
                                       cwd=cwd,
                                       stdout=stdout,
                                       stderr=stdout,
                                       on_closed=self.on_closed)
        BufferJobManager.create(self.job_name, param)


    def format(self, args: str | list, stdout, command_wrapper=None):
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()

        if isinstance(args, list):
            args = " ".join(map(str, args))
        command = f"ruff format {args}"
        cwd = get_current_directory()
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
        )
        stdout.init_buffer(result.stdout)

    def on_closed(self, buffer_job: BufferJobProtocol) -> None:
        assert buffer_job.stdout is not None
        messages = buffer_job.stdout.content
        qflist = self._make_qflist(messages)
        handle_records(
            PytoyQuickFix(cwd=buffer_job.cwd), records=qflist, win_id=None, is_open=True
        )

    def _make_qflist(self, string):
        records = []
        for line in string.split("\n"):
            match = self._pattern.match(line.strip())
            if not match:
                continue
            record = match.groupdict()
            records.append(record)
        return records
