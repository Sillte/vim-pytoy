import vim
import re

from pytoy.lib_tools.buffer_executor import BufferExecutor

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import PytoyBuffer, PytoyQuickFix

# def _set_focus(win_id: int, topline: int | None = None):
#    height = int(vim.eval(f"winheight({win_id})"))
#    if topline is None:
#        import json
#        info = json.loads(vim.eval(f"json_encode(getwininfo({win_id}))"))
#        topline = int(info[0]["topline"])
#    if topline <= 0:
#        topline = 1
#    centerline = topline + height // 2
#    vim.command(f"call win_execute({win_id}, 'call cursor({centerline},1)')")
#
# This kind of function should be implemented `PytoyBuffer`.
#


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
            args = " ".join(args)
        command = f"ruff check {args}"
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

    def _make_qflist(self, string):
        records = []
        for line in string.split("\n"):
            match = self._pattern.match(line.strip())
            if not match:
                continue
            record = match.groupdict()
            records.append(record)
        return records
