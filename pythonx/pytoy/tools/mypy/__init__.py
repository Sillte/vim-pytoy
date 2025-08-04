import re

from pytoy.lib_tools.buffer_executor import BufferExecutor

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import PytoyQuickFix, handle_records


class MypyExecutor(BufferExecutor):
    """Execute Mypy."""

    def __init__(self):
        self._pattern = re.compile(
            r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<_type>(.+)):(?P<text>(.+))"
        )

    def runfile(self, path, stdout, command_wrapper=None):
        """Execute `pytest` for only one file."""
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        command = f'mypy --show-traceback --show-column-numbers "{path}"'
        return super().run(command, stdout, stdout, command_wrapper=command_wrapper)

    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content

        qflist = self._make_qflist(messages)
        handle_records(PytoyQuickFix(), qflist, win_id=None, is_open=True)

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
