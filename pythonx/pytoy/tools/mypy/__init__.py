import re
from pathlib import Path

from pytoy.lib_tools.buffer_executor import (
    BufferJobProtocol,
    BufferJobCreationParam,
    BufferJobManager,
)
from pytoy.lib_tools.utils import get_current_directory


from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import PytoyQuickFix, handle_records


class MypyExecutor:
    """Execute Mypy."""

    job_name = "MypyExecutor"

    def __init__(self):
        self._pattern = re.compile(
            r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<_type>(.+)):(?P<text>(.+))"
        )

    def check(
        self, arg: list[str | Path] | str | Path, stdout, command_wrapper=None
    ) -> None:
        """Execute `pytest` for only one file."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        if isinstance(arg, (str, Path)):
            command = f'mypy --show-traceback --show-column-numbers "{arg}"'
        else:
            command = (
                f"mypy --show-traceback --show-column-numbers {' '.join(map(str, arg))}"
            )
        wrapped_command = command_wrapper(command)
        cwd = get_current_directory()
        param = BufferJobCreationParam(
            command=wrapped_command, stdout=stdout, cwd=cwd, on_closed=self.on_closed
        )
        BufferJobManager.create(self.job_name, param)

    def on_closed(self, buffer_job: BufferJobProtocol) -> None:
        assert buffer_job.stdout is not None
        messages = buffer_job.stdout.content
        qflist = self._make_qflist(messages)
        handle_records(
            PytoyQuickFix(cwd=buffer_job.cwd), qflist, win_id=None, is_open=True
        )

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
