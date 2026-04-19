from pytoy import TERM_STDOUT
from pytoy.job_execution.command_executor.launcher import CommandLauncher, LaunchProfile, get_default_hooks, ExecutionHooks
from pytoy.job_execution.command_executor.launcher.quickfix import QuickfixProfile, make_quickfix_hooks
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.tools.python.path_resolver import PathResolver


from typing import Literal


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
        hooks = ExecutionHooks.merge(hooks, make_quickfix_hooks(profile))

        profile = LaunchProfile(kind=self.kind, execution_hooks=hooks)
        launcher = CommandLauncher(profile)
        launcher.run(command, stdout=self.buffer)

    def rerun(self) -> None:
        launcher = CommandLauncher(self.kind)
        launcher.rerun(self.buffer)