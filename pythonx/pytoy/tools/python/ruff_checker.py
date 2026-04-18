from dataclasses import dataclass
from pathlib import Path

from pytoy import TERM_STDOUT
from pytoy.contexts.core import GlobalCoreContext
from pytoy.job_execution.command_executor.launcher import CommandLauncher, LaunchProfile
from pytoy.job_execution.command_executor.launcher.quickfix import QuickfixProfile, make_quickfix_hooks
from pytoy.job_execution.environment_manager import EnvironmentManager
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.tools.python.path_resolver import PathResolver
from typing import Literal


@dataclass(frozen=True)
class RuffFormatHistory:
    path: Path
    cwd: Path


class RuffChecker:
    def __init__(self, environment_manager: EnvironmentManager | None = None):
        self._environment_manager = environment_manager or GlobalCoreContext.get().environment_manager

    @property
    def environment_manager(self) -> EnvironmentManager:
        return self._environment_manager

    @property
    def kind(self):
        return "RuffChecker"

    def make_command(self, path: Path, fix: bool, unsafe: bool) -> str:
        option_str = ""
        if fix is True:
            option_str += " --fix "
        if unsafe is True:
            option_str += " --unsafe-fixes "
        return f'ruff check "{path}" --output-format=concise {option_str}'

    @property
    def buffer(self) -> PytoyBuffer:
        return make_buffer(TERM_STDOUT, "vertical")

    def check(self, target: Literal["workspace", "current"] | str | None, fix: bool, format: bool, unsafe: bool) -> None:
        current_path = PytoyBuffer.get_current().file_path
        cwd = current_path.parent

        path = PathResolver(self.environment_manager, cwd=cwd).resolve(target, current_path)

        pytoy_buffer = self.buffer

        if format:
            self._format(path, cwd, self.buffer)
            meta = {"format": RuffFormatHistory(path=path, cwd=cwd)}
        else:
            self.buffer.init_buffer()
            meta = {}

        qf_creator = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<text>(.+))"

        quickfix_profile = QuickfixProfile(quickfix_creator=qf_creator, quickfix_source="stdout")
        hooks = make_quickfix_hooks(quickfix_profile)

        profile = LaunchProfile(kind=self.kind, execution_hooks=hooks)
        launcher = CommandLauncher(profile)
        command = self.make_command(path, fix, unsafe)
        launcher.run(command, stdout=pytoy_buffer, cwd=cwd, meta=meta)

    def rerun(self) -> None:
        profile = LaunchProfile(kind=self.kind)
        launcher = CommandLauncher(profile)
        if (last_context := launcher.last_context):
            if (format:=last_context.meta.get("format")):
                self._format(format.path, format.cwd, self.buffer)
        launcher.rerun(self.buffer)

    def stop(self) -> None:
        profile = LaunchProfile(kind=self.kind)
        CommandLauncher(profile).stop()

    def _format(self, path: Path, cwd: Path, buffer: PytoyBuffer):
        import subprocess
        execution_env = self.environment_manager.solve_preference(cwd, preference=None)

        command = f'ruff format "{path}"'
        command = execution_env.command_wrapper(command)

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
        )
        buffer.init_buffer(result.stdout)