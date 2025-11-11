import re

from pytoy.lib_tools.buffer_executor import BufferExecutor

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.lib_tools.utils import get_current_directory
from pytoy.ui import PytoyQuickFix, handle_records


class RuffExecutor(BufferExecutor):
    """Execute Ruff."""

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
        return super().run(command, stdout, stdout, command_wrapper=command_wrapper, cwd=cwd)

    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content
        qflist = self._make_qflist(messages)
        handle_records(PytoyQuickFix(cwd=self.cwd), records=qflist, win_id=None, is_open=True)

    def _make_qflist(self, string):
        records = []
        for line in string.split("\n"):
            match = self._pattern.match(line.strip())
            if not match:
                continue
            record = match.groupdict()
            records.append(record)
        return records
