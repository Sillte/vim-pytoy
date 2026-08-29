from typing import Literal

from pytoy import TERM_STDOUT
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.tool_execution.command.launcher import (
    CommandExecutionHooks,
    CommandLauncher,
    LaunchProfile,
    get_default_hooks,
)
from pytoy.tool_execution.command.launcher.quickfix import QuickfixProfile, make_quickfix_hooks
from pytoy.tools.python.path_resolver import PathResolver


class MypyChecker:
    def __init__(self) -> None:
        pass

    @property
    def kind(self):
        return "MypyChecker"

    @property
    def buffer(self) -> PytoyBuffer:
        return make_buffer(TERM_STDOUT, "vertical")

    def check(self, target: Literal["workspace", "current"] | str | None = None):
        path = PathResolver().resolve(target)

        command = f'mypy --show-traceback --show-column-numbers "{path}"'

        quickfix_regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<_type>(.+)):(?P<text>(.+))"
        profile = QuickfixProfile(quickfix_creator=quickfix_regex)
        hooks = get_default_hooks()
        hooks = CommandExecutionHooks.merge(hooks, make_quickfix_hooks(profile))

        profile = LaunchProfile(kind=self.kind, execution_hooks=hooks)
        launcher = CommandLauncher(profile)
        launcher.run(command, stdout=self.buffer)

    def rerun(self) -> None:
        launcher = CommandLauncher(self.kind)
        launcher.rerun(self.buffer)
