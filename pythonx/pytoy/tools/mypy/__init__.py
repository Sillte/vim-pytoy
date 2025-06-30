import vim
import re

from pytoy.lib_tools.buffer_executor import BufferExecutor

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import PytoyQuickFix


def _handle_records(records: list[dict], is_open: bool):
    if records:
        PytoyQuickFix().setlist(records, win_id=None)
        if is_open:
            PytoyQuickFix().open(win_id=None)
    else:
        PytoyQuickFix().close(win_id=None)


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
        # stdout[0] = command
        return super().run(command, stdout, stdout, command_wrapper=command_wrapper)


    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content

        qflist = self._make_qflist(messages)
        _handle_records(qflist, is_open=True)


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
