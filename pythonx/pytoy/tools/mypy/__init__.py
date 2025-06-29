import vim
import re

from pytoy.lib_tools.buffer_executor import BufferExecutor

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import PytoyQuickFix



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

    def prepare(self):
        # I do not need to return any `dict` for customization.
        # But, it requires `win_id` at `on_closed`.
        self.win_id = vim.eval("win_getid()")
        return None

    def on_closed(self):
        assert self.stdout is not None
        messages = self.stdout.content

        qflist = self._make_qflist(messages)
        q_winid = _to_quickfix_winid(self.win_id)
        _handle_loclist(q_winid, qflist, is_open=True)

        # Scrolling output window
        # [NOTE ](2025/06/22): I feel this function is not necessary.
        # with store_cursor():
        #    self.stdout.focus()
        #    vim.command("normal zb")

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
